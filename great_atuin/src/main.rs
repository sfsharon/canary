use std::{thread, time::Duration};
use log::{info, debug, error};
use pcap::{Device, Capture};
use pnet::packet::{ethernet::EthernetPacket, Packet};
use hex;
use std::error::Error;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

// Constants
const ISIS_P2P_HELLO_TYPE: u8 = 17;
const ISIS_MULTICAST_MAC: [u8; 6] = [0x01, 0x80, 0xc2, 0x00, 0x00, 0x14];
const ETHERTYPE_ISIS: u16 = 0x83FE;
const HELLO_INTERVAL_SECS: u64 = 3;
const CAPTURE_TIMEOUT_MS: i32 = 5000;
const HOLD_TIME_SECS: u16 = 30;

#[derive(Debug, Copy, Clone)]
enum CircuitType {
    L1Only = 1,
    L2Only = 2,
    L1L2 = 3,
}

#[derive(Debug, Copy, Clone)]
enum PDUType {
    L1LanHello = 15,
    L2LanHello = 16,
    P2PHello = 17,
}

#[derive(Debug, thiserror::Error)]
enum ISISError {
    #[error("Device not found: {0}")]
    DeviceNotFound(String),
    #[error("Capture error: {0}")]
    CaptureError(String),
    #[error("Packet error: {0}")]
    PacketError(String),
}

// STRUCTS
// -------
#[derive(Debug)]
struct ISISConfig {
    interface: String,
    router_ip: String,
    net: String,
    hello_interval: Duration,
    capture_timeout: i32,
}

struct ISISPacketBuilder {
    buffer: Vec<u8>,
}

#[derive(Debug)]
struct ISISNeighborSimulator {
    config: ISISConfig,
    system_id: String,
    area_id: String,
}

// IMPLEMENTATIONS
// ---------------
impl Default for ISISConfig {
    fn default() -> Self {
        Self {
            interface: String::new(),
            router_ip: String::new(),
            net: String::new(),
            hello_interval: Duration::from_secs(HELLO_INTERVAL_SECS),
            capture_timeout: CAPTURE_TIMEOUT_MS,
        }
    }
}

impl ISISPacketBuilder {
    fn new() -> Self {
        Self { buffer: Vec::new() }
    }

    fn add_ethernet_header(&mut self) -> &mut Self {
        self.buffer.extend_from_slice(&ISIS_MULTICAST_MAC);
        self.buffer.extend_from_slice(&[0x00; 6]);
        self.buffer.extend_from_slice(&ETHERTYPE_ISIS.to_be_bytes());
        self
    }

    fn add_isis_header(&mut self, pdu_type: PDUType) -> &mut Self {
        self.buffer.push(0x83);  // Protocol ID
        self.buffer.push(pdu_type as u8);
        self.buffer.push(0x01);  // Version
        self.buffer.push(0x00);  // Reserved
        self
    }

    fn add_system_id(&mut self, system_id: &str) -> Result<&mut Self, Box<dyn Error>> {
        let system_id = system_id.replace(".", "");
        self.buffer.extend_from_slice(&hex::decode(&system_id)?);
        Ok(self)
    }

    fn build(self) -> Vec<u8> {
        self.buffer
    }
}


impl ISISNeighborSimulator {
    fn new(config: ISISConfig) -> Result<Self, Box<dyn Error>> {
        let system_id = config.net.get(3..15)
            .ok_or("Invalid NET format")?
            .to_string();
        let area_id = Self::extract_area_id(&config.net)?;
        
        Ok(Self {
            config,
            system_id,
            area_id,
        })
    }

    fn extract_area_id(net: &str) -> Result<String, Box<dyn Error>> {
        let parts: Vec<&str> = net.split('.').collect();
        if parts.len() < 2 {
            return Err("Invalid NET format".into());
        }
        let area_id = format!("{}.{}", parts[0], parts[1]);
        Ok(Self::format_area_id(&area_id))
    }

    fn format_area_id(area: &str) -> String {
        let parts: Vec<&str> = area.split('.').collect();
        parts.iter()
            .map(|part| format!("{:0>2}", part))
            .collect::<Vec<String>>()
            .join(".")
    }

    fn craft_hello_packet(&self) -> Result<Vec<u8>, Box<dyn Error>> {
        let mut builder = ISISPacketBuilder::new();
        builder
            .add_ethernet_header()
            .add_isis_header(PDUType::P2PHello);
        builder.add_system_id(&self.system_id)?;

        let mut packet = builder.build();

        // Add hold time
        packet.extend_from_slice(&HOLD_TIME_SECS.to_be_bytes());

        // TLVs
        // Area TLV
        packet.push(0x01);
        packet.push(self.area_id.len() as u8);
        packet.extend_from_slice(self.area_id.as_bytes());

        // Protocols Supported TLV
        packet.push(0x81);
        packet.push(0x01);
        packet.push(0xCC); // IPv4

        // IP Interface Address TLV
        packet.push(0x8E);
        let ip_bytes: Vec<u8> = self.config.router_ip
            .split('.')
            .map(|x| x.parse::<u8>().map_err(|e| e.to_string()))
            .collect::<Result<Vec<u8>, String>>()?;
        packet.push(ip_bytes.len() as u8);
        packet.extend_from_slice(&ip_bytes);

        // Padding TLV
        packet.push(0xFF);
        packet.push(0xFF);
        packet.extend_from_slice(&vec![0x00; 255]);

        Ok(packet)
    }

    fn send_hello(&self) -> Result<Vec<u8>, Box<dyn Error>> {
        let packet = self.craft_hello_packet()?;
        
        let interface = Device::list()?
            .into_iter()
            .find(|iface| iface.name == self.config.interface)
            .ok_or_else(|| ISISError::DeviceNotFound(self.config.interface.clone()))?;

        let mut cap = Capture::from_device(interface)?
            .immediate_mode(true)
            .open()?;

        cap.sendpacket(&*packet)?;
        info!("Sent ISIS Hello packet on interface {} with system ID {}", 
            self.config.interface, self.system_id);
        
        Ok(packet)
    }

    fn receive_hello(&self) -> Result<Option<Vec<u8>>, Box<dyn Error>> {
        let interface = Device::list()?
            .into_iter()
            .find(|iface| iface.name == self.config.interface)
            .ok_or_else(|| ISISError::DeviceNotFound(self.config.interface.clone()))?;

        let mut cap = Capture::from_device(interface)?
            .immediate_mode(true)
            .timeout(self.config.capture_timeout)
            .open()?;

        cap.filter("isis", true)?;

        match cap.next_packet() {
            Ok(packet) => Ok(Some(packet.data.to_vec())),
            Err(pcap::Error::TimeoutExpired) => Ok(None),
            Err(e) => Err(Box::new(ISISError::CaptureError(e.to_string())))
        }
    }

    fn verify_response(&self, _sent_packet: &[u8], received_packet: &[u8]) -> bool {
        if received_packet.len() < 14 {
            error!("Packet too short");
            return false;
        }

        let eth_packet = match EthernetPacket::new(received_packet) {
            Some(packet) => packet,
            None => {
                error!("Failed to parse Ethernet packet");
                return false;
            }
        };

        if eth_packet.get_ethertype().0 != ETHERTYPE_ISIS {
            error!("Not an ISIS packet");
            return false;
        }

        let payload = eth_packet.payload();
        if payload.len() < 3 {
            error!("ISIS payload too short");
            return false;
        }

        let pdu_type = payload[1];
        match pdu_type {
            15 => info!("Received L1 LAN Hello"),
            16 => info!("Received L2 LAN Hello"),
            17 => info!("Received P2P Hello"),
            _ => {
                error!("Not an ISIS Hello packet");
                return false;
            }
        }

        let circuit_type = payload[5];
        if ![1, 2, 3].contains(&circuit_type) {
            error!("Incorrect circuit type");
            return false;
        }

        debug!("Response verified successfully");
        true
    }

    pub fn run(&self, running: Arc<AtomicBool>) -> Result<(), Box<dyn Error>> {
        while running.load(Ordering::Relaxed) {
            let sent_packet = self.send_hello()?;
            
            match self.receive_hello()? {
                Some(received_packet) => {
                    if self.verify_response(&sent_packet, &received_packet) {
                        info!("Valid ISIS neighbor detected");
                    } else {
                        info!("Failed to verify ISIS neighbor");
                    }
                }
                None => info!("No response received"),
            }

            thread::sleep(self.config.hello_interval);
        }
        info!("ISIS Neighbor Simulator shutting down");
        Ok(())
    }
}

fn run_ut(simulator: &ISISNeighborSimulator) -> Result<(), Box<dyn Error>> {
    let received_isis_hello_pkt_str = "0180c2000015d077ceda710705d7fefe03831b01001001000002000701000003001e05d44000070100000306d301008102cc8e01040349097284040506070908ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008";
    let received_packet = hex::decode(received_isis_hello_pkt_str)?;
    let sent_packet = simulator.craft_hello_packet()?;
    
    simulator.verify_response(&sent_packet, &received_packet);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_system_id_extraction() {
        let config = ISISConfig {
            net: "49.0972.0007.0100.0004.00".to_string(),
            ..Default::default()
        };
        let simulator = ISISNeighborSimulator::new(config).unwrap();
        assert_eq!(simulator.system_id, "0007.0100.0004");
    }

    #[test]
    fn test_area_id_formatting() {
        assert_eq!(
            ISISNeighborSimulator::format_area_id("49.972"),
            "49.972"
        );
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    // Initialize logging
    env_logger::init();

    const MODE_UT: u8 = 1;
    const MODE_OPERATIONAL: u8 = 2;
    let sim_mode = MODE_UT;

    let config = ISISConfig {
        interface: "enp4s0f1".to_string(),
        router_ip: "5.6.7.9".to_string(),
        net: "49.0972.0007.0100.0004.00".to_string(),
        hello_interval: Duration::from_secs(HELLO_INTERVAL_SECS),
        capture_timeout: CAPTURE_TIMEOUT_MS,
    };

    let simulator = ISISNeighborSimulator::new(config)?;
    let running = Arc::new(AtomicBool::new(true));
    let running_clone = running.clone();

    // Set up signal handler for graceful shutdown
    ctrlc::set_handler(move || {
        info!("Received shutdown signal");
        running_clone.store(false, Ordering::Relaxed);
    })?;

    match sim_mode {
        MODE_OPERATIONAL => simulator.run(running)?,
        MODE_UT => run_ut(&simulator)?,
        _ => unreachable!(),
    }

    info!("End of ISIS Neighbor Simulator Run");
    Ok(())
}
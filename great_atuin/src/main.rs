use std::{thread, time::Duration};
use log::{info, debug, error};
use pcap::{Device, Capture};
use pnet::packet::{ethernet::{EthernetPacket, MutableEthernetPacket}, Packet};
use hex;

// Constants
const ISIS_P2P_HELLO_TYPE: u8 = 17;
const ISIS_MULTICAST_MAC: [u8; 6] = [0x01, 0x80, 0xc2, 0x00, 0x00, 0x14];
const ETHERTYPE_ISIS: u16 = 0x83FE;

#[derive(Debug)]
struct ISISNeighborSimulator {
    interface: String,
    router_ip: String,
    net: String,
    system_id: String,
    area_id: String,
}

impl ISISNeighborSimulator {
    fn new(interface: &str, router_ip: &str, net: &str) -> Self {
        let system_id = net[3..15].to_string();
        let area_id = Self::extract_area_id(net);
        
        Self {
            interface: interface.to_string(),
            router_ip: router_ip.to_string(),
            net: net.to_string(),
            system_id,
            area_id,
        }
    }

    fn extract_area_id(net: &str) -> String {
        let parts: Vec<&str> = net.split('.').collect();
        let area_id = format!("{}.{}", parts[0], parts[1]);
        Self::format_area_id(&area_id)
    }

    fn format_area_id(area: &str) -> String {
        let parts: Vec<&str> = area.split('.').collect();
        parts.iter()
            .map(|part| format!("{:0>2}", part))
            .collect::<Vec<String>>()
            .join(".")
    }

    fn craft_hello_packet(&self) -> Vec<u8> {
        let mut packet = Vec::new();
        
        // Ethernet Header
        packet.extend_from_slice(&ISIS_MULTICAST_MAC); // Destination MAC
        // Source MAC will be added by the network interface
        packet.extend_from_slice(&[0x00, 0x00, 0x00, 0x00, 0x00, 0x00]);
        packet.extend_from_slice(&ETHERTYPE_ISIS.to_be_bytes());

        // ISIS Common Header
        packet.push(0x83); // Protocol ID
        packet.push(ISIS_P2P_HELLO_TYPE); // PDU Type
        packet.push(0x01); // Version/Protocol ID Extension
        packet.push(0x00); // Reserved
        packet.push(0x10); // Length Indicator
        
        // ISIS P2P Hello
        packet.push(0x02); // Circuit Type (L2 only)
        packet.extend_from_slice(&hex::decode(&self.system_id).unwrap()); // System ID
        packet.extend_from_slice(&[0x00, 0x1E]); // Hold Time (30 seconds)

        // TLVs
        // Area TLV
        packet.push(0x01); // Type
        packet.push(self.area_id.len() as u8); // Length
        packet.extend_from_slice(self.area_id.as_bytes());

        // Protocols Supported TLV
        packet.push(0x81); // Type
        packet.push(0x01); // Length
        packet.push(0xCC); // IPv4

        // IP Interface Address TLV
        packet.push(0x8E); // Type
        let ip_bytes: Vec<u8> = self.router_ip
            .split('.')
            .map(|x| x.parse::<u8>().unwrap())
            .collect();
        packet.push(ip_bytes.len() as u8); // Length
        packet.extend_from_slice(&ip_bytes);

        // Padding TLV
        packet.push(0xFF); // Type
        packet.push(0xFF); // Length
        packet.extend_from_slice(&vec![0x00; 255]); // Padding

        packet
    }

    fn send_hello(&self) -> Vec<u8> {
        let packet = self.craft_hello_packet();
        
        // Open the network interface
        let interface = Device::list()
            .unwrap()
            .into_iter()
            .find(|iface| iface.name == self.interface)
            .expect("Failed to find interface");

        let mut cap = Capture::from_device(interface)
            .unwrap()
            .immediate_mode(true)
            .open()
            .unwrap();

        cap.sendpacket(&packet).expect("Failed to send packet");
        info!("Sent ISIS Hello packet");
        
        packet
    }

    fn receive_hello(&self) -> Option<Vec<u8>> {
        let interface = Device::list()
            .unwrap()
            .into_iter()
            .find(|iface| iface.name == self.interface)
            .expect("Failed to find interface");

        let mut cap = Capture::from_device(interface)
            .unwrap()
            .immediate_mode(true)
            .timeout(5000)
            .open()
            .unwrap();

        // Set filter for ISIS packets
        cap.filter("isis", true).expect("Failed to set filter");

        match cap.next_packet() {
            Ok(packet) => {
                Some(packet.data.to_vec())
            }
            Err(_) => None
        }
    }

    fn verify_response(&self, sent_packet: &[u8], received_packet: &[u8]) -> bool {
        if received_packet.len() < 14 {
            error!("Packet too short");
            return false;
        }

        // Parse Ethernet frame
        let eth_packet = EthernetPacket::new(received_packet)
            .expect("Failed to parse Ethernet packet");

        // Check if it's an ISIS packet
        if eth_packet.get_ethertype().0 != ETHERTYPE_ISIS {
            error!("Not an ISIS packet");
            return false;
        }

        let payload = eth_packet.payload();
        if payload.len() < 3 {
            error!("ISIS payload too short");
            return false;
        }

        // Check PDU type
        let pdu_type = payload[1];
        if ![15, 16, 17].contains(&pdu_type) {
            error!("Not an ISIS Hello packet");
            return false;
        }

        // Log the type of Hello received
        match pdu_type {
            15 => info!("### Received L1 LAN Hello"),
            16 => info!("### Received L2 LAN Hello"),
            17 => info!("### Received P2P Hello"),
            _ => unreachable!(),
        }

        // Verify circuit type
        let circuit_type = payload[5];
        if ![1, 2, 3].contains(&circuit_type) {
            error!("Incorrect circuit type");
            return false;
        }

        debug!("Response verified successfully");
        true
    }

    pub fn run(&self) {
        loop {
            let sent_packet = self.send_hello();
            
            match self.receive_hello() {
                Some(received_packet) => {
                    if self.verify_response(&sent_packet, &received_packet) {
                        info!("Valid ISIS neighbor detected");
                    } else {
                        info!("Failed to verify ISIS neighbor");
                    }
                }
                None => info!("### No response received"),
            }

            thread::sleep(Duration::from_secs(3));
        }
    }
}

fn run_ut(simulator: &ISISNeighborSimulator) {
    let received_isis_hello_pkt_str = "0180c2000015d077ceda710705d7fefe03831b01001001000002000701000003001e05d44000070100000306d301008102cc8e01040349097284040506070908ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008ff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000089f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000";
    let received_packet = hex::decode(received_isis_hello_pkt_str).unwrap();
    let sent_packet = simulator.craft_hello_packet();
    
    simulator.verify_response(&sent_packet, &received_packet);
}

fn main() {
    // Initialize logging
    env_logger::init();

    const MODE_UT: u8 = 1;
    const MODE_OPERATIONAL: u8 = 2;
    let sim_mode = MODE_UT;

    let simulator = ISISNeighborSimulator::new(
        "enp4s0f1",
        "5.6.7.9",
        "49.0972.0007.0100.0004.00"
    );

    match sim_mode {
        MODE_OPERATIONAL => simulator.run(),
        MODE_UT => run_ut(&simulator),
        _ => unreachable!(),
    }

    info!("End of ISIS Neighbor Simulator Run");
}
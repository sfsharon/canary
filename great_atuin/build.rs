/*
libpcap needs to be compiled to a static library with MUSL for x86, so that "cargo build --target x86_64-unknown-linux-musl"
will work when linking the pnet crate.
Succeeded doing it only by using the Alpine docker.
Required :
1. Install docker on the WSL Ubuntu machine.
2. Compile with docker :
    1. create a new directory for our Docker build:
    mkdir docker_libpcap_build
    cd docker_libpcap_build

    2. Create a Dockerfile:
        cat > Dockerfile << 'EOF'
        FROM alpine:latest

        # Install build dependencies
        RUN apk add --no-cache \
            build-base \
            linux-headers \
            flex \
            bison \
            libpcap-dev \
            musl-dev

        WORKDIR /build
        EOF

    3. Download libpcap source:
        wget https://www.tcpdump.org/release/libpcap-1.10.4.tar.gz
        tar xvf libpcap-1.10.4.tar.gz

    4. Build the Docker image:
        docker build -t pcap-musl-builder .

    5. Run the container to build libpcap:
        docker run -v $PWD/libpcap-1.10.4:/build pcap-musl-builder sh -c "cd /build && ./configure --prefix=/usr --enable-static --disable-shared && make"

3. Move the compiled libpcap.a file to an agreed upon place :
    cd libpcap-1.10.4
    ls -l libpcap.a
    sudo mkdir -p /usr/local/musl/lib
    sudo cp libpcap.a /usr/local/musl/lib/

4. Try building your Rust project again with:
    cargo build --target x86_64-unknown-linux-musl
*/

fn main() {
    // Tell cargo to look for libraries in /usr/local/musl/lib
    println!("cargo:rustc-link-search=native=/usr/local/musl/lib");
    
    // Tell cargo to statically link against pcap
    println!("cargo:rustc-link-lib=static=pcap");
    
    // Tell cargo to rerun this build script if build.rs changes
    println!("cargo:rerun-if-changed=build.rs");
}
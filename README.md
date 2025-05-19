# Peer-to-Peer File Transfer App

## Overview

This project is a peer-to-peer (P2P) file sharing application. It allows users to connect to a network of peers, search for files, download files from other peers, and share their own files with the network.  This is a foundational project for understanding distributed systems and networking concepts.

## Features

* **Peer Discovery:** The application facilitates finding other peers on the network.  This is crucial for establishing connections and enabling file sharing.
* **File Search:** Users can search for files available on the P2P network. The search functionality queries connected peers and aggregates results.
* **File Download:** Downloads files directly from other peers.  This is the core function of a P2P application.
* **File Sharing:** Users can share files from their local system, making them available to other peers on the network.
* **Decentralized Architecture:** The application operates without a central server, distributing resources and responsibilities across peers.
* **Basic UI:** A simple user interface to interact with the application, showing connected peers, search results, and download progress.

## Technical Details
* **Programming Languages:**
    * **Frontend:** TypeScript
    * **Backend:** Python
* **Frameworks/Libraries:**
    * **Frontend:** Electron, Yarn
* **Networking**: The application uses websockets for network communication between peers.
* **Protocol:** A custom protocol is used for peer communication, including file search requests, file transfer, and peer discovery.
* **Threading/Async:** The application uses multi-threading (in Python) and asynchronous operations (in TypeScript) to handle concurrent operations, such as managing multiple connections and downloads simultaneously.

## System Design
![System Design](./system-design.png)

## Getting Started

### Prerequisites

* **Python v3.9+**
* **Node.js v19+**

### Running the app (dev)
1. **Clone the Repository:**
    ```bash
    git clone [https://github.com/metharda/p2p-file-transfer](https://github.com/metharda/p2p-file-transfer))
    cd p2p-file-transfer
    ```
2. **Install Backend Dependencies and Start the Backend**
    ```bash
    cd python-backend
    python3 -m venv your-venv #If don't want to use python virtual environment you can skip this step
    pip install -r requirements.txt
    python3 main.py
    ```
3. **Install Frontend Dependencies and Start the Frontend**
   ```bash
   cd electron-frontend
   yarn install
   yarn dev
   ```
### Building the app (Not Finished)
Docker is working currently and can successfully run a container, but the GUI doens't work on devices. Its possible to build frontend with yarn build but you still need to start backend independently.

## Usage
The application provides a user-friendly GUI for interacting with the P2P network. Usage is fairly simple:
* **File Search:** Enter the name of the file you want to download from the network and if any peer has that file, select a download location to save the file.
* **File Search with List** You can create a .txt file containing names of files you want to download and with a simple "drag&drop or select" box you can easily download all files in the list simultaneously, if any peer has these files.
* **Publicly Shared Folder** In backend folder you can put any file you want to share with the network in publicFiles folder. It flags any file in that folder as downloadable.

## Future Plans
* **Improved UI:** A more user-friendly and feature-rich graphical user interface (GUI).
* **Advanced Search:** Support for more advanced search options, such as filtering by file type, size, or other criteria.
* **Security:** Enhanced security features, such as encryption and authentication, to protect against malicious peers and data corruption.
* **Performance:** Optimizations for improved performance, such as faster downloads and more efficient network communication.
* **More Robust Peer Discovery:** Implement more sophisticated peer discovery mechanisms.
* **Testing:** Add unit and integration tests.
* **Documentation:** Add more detailed documentation.
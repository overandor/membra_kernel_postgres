import Cocoa
import FinderSync

class FinderSync: FIFinderSync {
    var myFolderURL: URL?
    var backendURL: String {
        // Read from UserDefaults or use default
        return UserDefaults.standard.string(forKey: "backendURL") ?? "http://localhost:8000"
    }
    
    override init() {
        self.myFolderURL = URL(fileURLWithPath: "/Users")
        super.init()
        
        // Monitor the user's home directory
        FIFinderSyncController.default().directoryURLs = [self.myFolderURL!]
    }
    
    override var toolbarItemName: String {
        return "Membra Folder Link"
    }
    
    override var toolbarItemToolTip: String {
        return "Create a public link for this folder"
    }
    
    override var toolbarItemImage: NSImage {
        return NSImage(systemSymbolName: "link", accessibilityDescription: "Create Public Link") ?? NSImage(named: NSImage.actionTemplateName)!
    }
    
    override func menu(for menuKind: FIMenuKind) -> NSMenu {
        let menu = NSMenu()
        
        if menuKind == .contextualMenuForItems {
            menu.addItem(withTitle: "Create Public Link", action: #selector(createPublicLink(_:)), keyEquivalent: "")
            menu.addItem(NSMenuItem.separator())
            menu.addItem(withTitle: "Create Private Link", action: nil, keyEquivalent: "")
            menu.addItem(withTitle: "Create Proof Page", action: nil, keyEquivalent: "")
            menu.addItem(NSMenuItem.separator())
            menu.addItem(withTitle: "Anchor Folder Proof to Solana Devnet", action: nil, keyEquivalent: "")
            menu.addItem(NSMenuItem.separator())
            menu.addItem(withTitle: "Revoke Shared Link", action: nil, keyEquivalent: "")
        }
        
        return menu
    }
    
    @objc func createPublicLink(_ sender: AnyObject?) {
        let target = FIFinderSyncController.default().targetedURL()
        guard let targetURL = target else {
            showAlert(message: "No folder selected")
            return
        }
        
        // Show configuration modal
        let alert = NSAlert()
        alert.messageText = "Create Public Link"
        alert.informativeText = "Folder: \(targetURL.path)"
        
        alert.addButton(withTitle: "Create")
        alert.addButton(withTitle: "Cancel")
        
        // Add expiration dropdown
        let expirationPopup = NSPopUpButton(frame: NSRect(x: 0, y: 0, width: 200, height: 24))
        expirationPopup.addItems(withTitles: ["Never", "24 hours", "7 days", "30 days"])
        alert.accessoryView = expirationPopup
        
        let response = alert.runModal()
        
        if response == .alertFirstButtonContinue {
            let expiration = expirationPopup.titleOfSelectedItem ?? "Never"
            createShare(for: targetURL, expiration: expiration)
        }
    }
    
    func createShare(for url: URL, expiration: String) {
        let expirationMap = ["Never": "never", "24 hours": "24h", "7 days": "7d", "30 days": "30d"]
        let expValue = expirationMap[expiration] ?? "never"
        
        let payload: [String: Any] = [
            "folder_path": url.path,
            "owner_wallet": "local_user",
            "expiration": expValue,
            "download_allowed": true,
            "index_enabled": true,
            "proof_manifest_enabled": true,
            "qr_enabled": true,
            "solana_anchor": false,
            "base_url": backendURL
        ]
        
        guard let requestURL = URL(string: "\(backendURL)/api/share/folder") else { return }
        var request = URLRequest(url: requestURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        } catch {
            showAlert(message: "Failed to encode request: \(error.localizedDescription)")
            return
        }
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                if let error = error {
                    self.showAlert(message: "Error: \(error.localizedDescription)")
                    return
                }
                
                guard let httpResponse = response as? HTTPURLResponse else {
                    self.showAlert(message: "Invalid response")
                    return
                }
                
                if httpResponse.statusCode == 200, let data = data {
                    do {
                        if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                           let publicLink = json["public_link"] as? String {
                            self.showSuccessAlert(link: publicLink)
                        }
                    } catch {
                        self.showAlert(message: "Failed to parse response")
                    }
                } else {
                    self.showAlert(message: "Server returned error: \(httpResponse.statusCode)")
                }
            }
        }
        
        task.resume()
    }
    
    func showAlert(message: String) {
        let alert = NSAlert()
        alert.messageText = "Membra Folder Link"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
    
    func showSuccessAlert(link: String) {
        let alert = NSAlert()
        alert.messageText = "Public Link Created"
        alert.informativeText = "Share URL: \(link)"
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Copy")
        alert.addButton(withTitle: "Open in Browser")
        alert.addButton(withTitle: "OK")
        
        let response = alert.runModal()
        
        if response == .alertFirstButtonReturn {
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(link, forType: .string)
        } else if response == .alertSecondButtonReturn {
            NSWorkspace.shared.open(URL(string: link)!)
        }
    }
}

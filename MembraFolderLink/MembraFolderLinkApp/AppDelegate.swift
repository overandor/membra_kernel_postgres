import Cocoa

@main
class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem?
    
    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Create status bar item
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        
        if let button = statusItem?.button {
            button.image = NSImage(systemSymbolName: "link.circle.fill", accessibilityDescription: "Membra")
            button.action = #selector(statusItemClicked)
        }
        
        // Show welcome window
        showWelcomeWindow()
    }
    
    func applicationWillTerminate(_ aNotification: Notification) {
        // Insert code here to tear down your application
    }
    
    @objc func statusItemClicked() {
        showWelcomeWindow()
    }
    
    @objc func saveBackendURL(_ sender: NSButton) {
        // Find the backend field and save its value
        if let contentView = sender.superview,
           let backendField = contentView.subviews.first(where: { $0 is NSTextField && $0.frame.origin.x == 120 }) as? NSTextField {
            UserDefaults.standard.set(backendField.stringValue, forKey: "backendURL")
            
            let alert = NSAlert()
            alert.messageText = "Backend URL Saved"
            alert.informativeText = "The extension will now use: \(backendField.stringValue)"
            alert.alertStyle = .informational
            alert.addButton(withTitle: "OK")
            alert.runModal()
        }
    }
    
    func showWelcomeWindow() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 500, height: 400),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.center()
        window.title = "Membra Folder Link"
        window.isReleasedWhenClosed = false
        
        let contentView = NSView(frame: window.contentView!.bounds)
        window.contentView = contentView
        
        // Title
        let titleField = NSTextField(labelWithString: "Membra Folder Link")
        titleField.font = NSFont.systemFont(ofSize: 24, weight: .bold)
        titleField.frame = NSRect(x: 20, y: 340, width: 460, height: 30)
        contentView.addSubview(titleField)
        
        // Description
        let descField = NSTextField(wrappingLabelWithString: "Right-click any folder in Finder to create a public share link with file hashes, proof manifest, and optional Solana anchoring.")
        descField.frame = NSRect(x: 20, y: 280, width: 460, height: 50)
        contentView.addSubview(descField)
        
        // Status
        let statusField = NSTextField(labelWithString: "Extension Status: Active")
        statusField.frame = NSRect(x: 20, y: 240, width: 460, height: 24)
        statusField.textColor = .systemGreen
        contentView.addSubview(statusField)
        
        // Backend URL
        let backendLabel = NSTextField(labelWithString: "Backend URL:")
        backendLabel.frame = NSRect(x: 20, y: 200, width: 100, height: 24)
        contentView.addSubview(backendLabel)
        
        let savedBackendURL = UserDefaults.standard.string(forKey: "backendURL") ?? "http://localhost:8000"
        let backendField = NSTextField(string: savedBackendURL)
        backendField.frame = NSRect(x: 120, y: 200, width: 360, height: 24)
        contentView.addSubview(backendField)
        
        // Save button
        let saveButton = NSButton(frame: NSRect(x: 20, y: 170, width: 80, height: 24))
        saveButton.title = "Save"
        saveButton.target = self
        saveButton.action = #selector(saveBackendURL(_:))
        contentView.addSubview(saveButton)
        
        // Instructions
        let instructions = """
To use Membra Folder Link:

1. Ensure the MEMBRA backend is running
2. Right-click any folder in Finder
3. Select "Create Public Link"
4. Configure expiration and options
5. Share the generated URL

The extension integrates with Finder's context menu to provide instant folder sharing capabilities.
"""
        let instructionsField = NSTextView(frame: NSRect(x: 20, y: 20, width: 460, height: 160))
        instructionsField.string = instructions
        instructionsField.isEditable = false
        instructionsField.backgroundColor = .clear
        instructionsField.font = NSFont.systemFont(ofSize: 12)
        contentView.addSubview(instructionsField)
        
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}

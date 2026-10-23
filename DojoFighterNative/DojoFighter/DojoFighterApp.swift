import SwiftUI

@main
struct DojoFighterApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        #if os(macOS)
        .defaultSize(width: 1280, height: 800)
        .windowStyle(.automatic)
        #endif
    }
}

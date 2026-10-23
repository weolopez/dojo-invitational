import SwiftUI

struct ContentView: View {
    @StateObject private var sceneController = FighterSceneController()

    var body: some View {
        ZStack {
            FighterArenaView(controller: sceneController)
                .ignoresSafeArea()

            FightHUDView(controller: sceneController)
        }
        .background(Color.black)
        .preferredColorScheme(.dark)
        #if os(macOS)
        .focusable()
        .onKeyPress(keys: Self.trackedKeys, phases: .down) { press in
            sceneController.handleKeyDown(press.key)
            return .handled
        }
        .onKeyPress(keys: Self.trackedKeys, phases: .up) { press in
            sceneController.handleKeyUp(press.key)
            return .handled
        }
        #endif
    }

    #if os(macOS)
    private static let trackedKeys: Set<KeyEquivalent> = [
        "w", "a", "s", "d",
        "W", "A", "S", "D",
        "1", "2", "3", "4", "5", "6",
        " ", "\t",
        .upArrow, .downArrow, .leftArrow, .rightArrow
    ]
    #endif
}

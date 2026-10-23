import SwiftUI
import RealityKit

struct FighterArenaView: View {
    @ObservedObject var controller: FighterSceneController

    var body: some View {
        RealityView { content in
            content.add(controller.makeSceneRoot())
        }
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { value in
                    // Relative delta from last translation step
                    let dx = value.translation.width
                    let dy = value.translation.height
                    // Use predicted incremental feel via velocity-ish small steps
                    controller.handleOrbit(
                        deltaX: dx * 0.02,
                        deltaY: -dy * 0.02
                    )
                }
        )
        .simultaneousGesture(
            MagnificationGesture()
                .onChanged { scale in
                    // Map magnification to zoom nudges
                    let delta = (1.0 - scale) * 2.0
                    controller.handleZoom(delta: delta)
                }
        )
        #if os(macOS)
        .onAppear {
            NSEvent.addLocalMonitorForEvents(matching: .scrollWheel) { event in
                controller.handleZoom(delta: event.scrollingDeltaY)
                return event
            }
        }
        #endif
    }
}

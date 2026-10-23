import Foundation
import RealityKit
import simd

/// Simple orbit / action camera that drives an `PerspectiveCamera` entity.
@MainActor
final class CameraRig {
    let camera: PerspectiveCamera
    private(set) var mode: CameraMode = .orbit

    var target: SIMD3<Float> = [0, 1.15, 0]
    var distance: Float = 5.2
    var yaw: Float = 0.55
    var pitch: Float = 0.35
    var minDistance: Float = 2.0
    var maxDistance: Float = 12.0

    /// Optional focus entity for action cam (fighter root).
    weak var focusEntity: Entity?

    init() {
        camera = PerspectiveCamera()
        camera.camera.fieldOfViewInDegrees = 42
        applyTransform()
    }

    func setMode(_ mode: CameraMode) {
        self.mode = mode
        if mode == .action {
            yaw = 0.35
            pitch = 0.22
            distance = 4.4
        }
        applyTransform()
    }

    func orbit(deltaX: Float, deltaY: Float) {
        guard mode == .orbit else { return }
        yaw += deltaX * 0.01
        pitch = max(-0.2, min(1.2, pitch + deltaY * 0.01))
        applyTransform()
    }

    func zoom(delta: Float) {
        distance = max(minDistance, min(maxDistance, distance + delta))
        applyTransform()
    }

    func update(deltaTime: Float) {
        if mode == .action, let focus = focusEntity {
            let pos = focus.position(relativeTo: nil)
            target = SIMD3<Float>(pos.x, pos.y + 1.1, pos.z)
            yaw += deltaTime * 0.15
        }
        applyTransform()
    }

    private func applyTransform() {
        let cp = cos(pitch)
        let sp = sin(pitch)
        let cy = cos(yaw)
        let sy = sin(yaw)

        let offset = SIMD3<Float>(
            distance * cp * sy,
            distance * sp,
            distance * cp * cy
        )
        let eye = target + offset
        camera.look(at: target, from: eye, relativeTo: nil)
    }
}

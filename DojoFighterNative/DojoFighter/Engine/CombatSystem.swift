import Foundation
import RealityKit
import simd

/// Plays combat clips, footwork, and simple bag/opponent hit feedback.
@MainActor
final class CombatSystem {
    private weak var fighterRoot: Entity?
    private weak var bagEntity: Entity?
    private var animationLibrary: [String: AnimationResource] = [:]
    private var activeController: AnimationPlaybackController?
    private var bagPulseTime: Float = 0
    private var bagBaseScale: SIMD3<Float> = .one

    var animationSpeed: Float = 1.0 {
        didSet { activeController?.speed = animationSpeed }
    }

    func attach(
        fighter: Entity,
        bag: Entity?,
        animations: [String: AnimationResource]
    ) {
        fighterRoot = fighter
        bagEntity = bag
        animationLibrary = animations
        if let bag {
            bagBaseScale = bag.scale
        }
        play(.stance)
    }

    @discardableResult
    func play(_ move: CombatMove) -> Bool {
        guard let fighter = fighterRoot else { return false }

        if let clip = ModelLoader.matchAnimation(hints: move.animationHints, in: animationLibrary) {
            let controller = fighter.playAnimation(
                clip.repeat(count: move.isLooping ? nil : 1),
                transitionDuration: 0.18,
                startsPaused: false
            )
            controller.speed = animationSpeed
            activeController = controller
            return true
        }

        // Procedural fallback: small squash / lunge so the app feels alive without clips
        Task { await proceduralStrike(move, on: fighter) }
        return false
    }

    func moveFighter(direction: SIMD3<Float>, deltaTime: Float) {
        guard let fighter = fighterRoot else { return }
        let speed: Float = 2.4
        var pos = fighter.position
        pos += direction * speed * deltaTime

        // Keep fighter near the octagon mat
        let radius: Float = 3.2
        let planar = SIMD2<Float>(pos.x, pos.z)
        let len = simd_length(planar)
        if len > radius {
            let clamped = simd_normalize(planar) * radius
            pos.x = clamped.x
            pos.z = clamped.y
        }
        pos.y = 0
        fighter.position = pos

        if simd_length(direction) > 0.01 {
            let yaw = atan2(direction.x, direction.z)
            fighter.orientation = simd_quatf(angle: yaw, axis: [0, 1, 0])
        }
    }

    func strikeImpact() {
        bagPulseTime = 0.35
        guard let bag = bagEntity else { return }
        bag.scale = bagBaseScale * 1.08
    }

    func update(deltaTime: Float) {
        guard bagPulseTime > 0, let bag = bagEntity else { return }
        bagPulseTime = max(0, bagPulseTime - deltaTime)
        let t = bagPulseTime / 0.35
        let wobble = 1.0 + 0.08 * t * sin(bagPulseTime * 40)
        bag.scale = bagBaseScale * wobble
        if bagPulseTime == 0 {
            bag.scale = bagBaseScale
        }
    }

    private func proceduralStrike(_ move: CombatMove, on fighter: Entity) async {
        let original = fighter.transform
        var lunge = original
        let amount: Float = move == .roundhouse ? 0.35 : 0.22
        lunge.translation += SIMD3<Float>(0, 0, amount)
        fighter.move(to: lunge, relativeTo: fighter.parent, duration: 0.08)
        try? await Task.sleep(nanoseconds: 90_000_000)
        fighter.move(to: original, relativeTo: fighter.parent, duration: 0.12)
    }
}

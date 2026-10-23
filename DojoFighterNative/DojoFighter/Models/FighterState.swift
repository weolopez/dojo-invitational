import Foundation
import simd

enum CameraMode: String, CaseIterable, Identifiable {
    case orbit
    case action

    var id: String { rawValue }

    var title: String {
        switch self {
        case .orbit: return "Orbit Cam"
        case .action: return "Action Cam"
        }
    }
}

@MainActor
final class FighterState: ObservableObject {
    @Published var playerHealth: Float = 100
    @Published var opponentHealth: Float = 100
    @Published var comboCount: Int = 0
    @Published var comboBanner: String = ""
    @Published var activeMove: CombatMove = .stance
    @Published var cameraMode: CameraMode = .orbit
    @Published var animationSpeed: Float = 1.0
    @Published var statusMessage: String = "Loading dojo…"
    @Published var modelLoaded: Bool = false
    @Published var usingProceduralFallback: Bool = false

    let maxHealth: Float = 100

    var playerHealthRatio: Double {
        Double(max(0, min(1, playerHealth / maxHealth)))
    }

    var opponentHealthRatio: Double {
        Double(max(0, min(1, opponentHealth / maxHealth)))
    }

    func resetMatch() {
        playerHealth = maxHealth
        opponentHealth = maxHealth
        comboCount = 0
        comboBanner = ""
        activeMove = .stance
    }

    func registerHit(damage: Float, label: String) {
        guard damage > 0 else { return }
        opponentHealth = max(0, opponentHealth - damage)
        comboCount += 1
        comboBanner = label.isEmpty ? "HIT!" : label
    }

    func clearBanner() {
        comboBanner = ""
    }
}

import Foundation

/// Combat moves mapped to keyboard shortcuts and optional USDZ animation clip names.
enum CombatMove: String, CaseIterable, Identifiable, Codable {
    case stance
    case jabCross
    case roundhouse
    case uppercut
    case flurry
    case victory

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .stance: return "Fighting Stance"
        case .jabCross: return "Jab–Cross"
        case .roundhouse: return "Roundhouse"
        case .uppercut: return "Uppercut"
        case .flurry: return "Flurry"
        case .victory: return "Victory"
        }
    }

    var hotkey: String {
        switch self {
        case .stance: return "1"
        case .jabCross: return "2"
        case .roundhouse: return "3"
        case .uppercut: return "4"
        case .flurry: return "5"
        case .victory: return "6"
        }
    }

    /// Names to match against loaded RealityKit / USDZ animation resources.
    var animationHints: [String] {
        switch self {
        case .stance:
            return ["stance", "idle", "fighting_idle", "FightingStance", "Armature|stance"]
        case .jabCross:
            return ["jabcross", "jab_cross", "JabCross", "punch_combo", "Armature|jabcross"]
        case .roundhouse:
            return ["roundhouse", "roundhouse_kick", "kick", "Armature|kick"]
        case .uppercut:
            return ["uppercut", "power_uppercut", "Armature|uppercut"]
        case .flurry:
            return ["flurry", "speed_flurry", "punch_combo", "Armature|flurry"]
        case .victory:
            return ["victory", "taunt", "Armature|victory"]
        }
    }

    var isLooping: Bool {
        self == .stance
    }

    var damage: Float {
        switch self {
        case .stance: return 0
        case .jabCross: return 8
        case .roundhouse: return 16
        case .uppercut: return 18
        case .flurry: return 12
        case .victory: return 0
        }
    }

    var comboLabel: String {
        switch self {
        case .stance: return ""
        case .jabCross: return "JAB CROSS!"
        case .roundhouse: return "ROUNDHOUSE!"
        case .uppercut: return "UPPERCUT!"
        case .flurry: return "FLURRY!"
        case .victory: return "VICTORY!"
        }
    }
}

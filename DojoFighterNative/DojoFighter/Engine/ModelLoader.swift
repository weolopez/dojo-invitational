import Foundation
import RealityKit

enum ModelLoadError: LocalizedError {
    case missingResource(String)
    case loadFailed(String)

    var errorDescription: String? {
        switch self {
        case .missingResource(let name):
            return "Missing model resource: \(name)"
        case .loadFailed(let detail):
            return "Failed to load model: \(detail)"
        }
    }
}

enum ModelLoader {
    /// Preferred bundle resource names (without extension).
    static let arenaModelName = "fullbody_fighter_arena"
    static let avatarModelName = "user_hyperrealistic_avatar"

    /// Load a USDZ/USD entity from the app bundle, then fall back to repo-relative paths in DEBUG.
    static func loadEntity(named name: String) async throws -> Entity {
        let extensions = ["usdz", "usd", "reality"]

        for ext in extensions {
            if let url = Bundle.main.url(forResource: name, withExtension: ext) {
                return try await loadEntity(from: url)
            }
            if let url = Bundle.main.url(forResource: name, withExtension: ext, subdirectory: "Models") {
                return try await loadEntity(from: url)
            }
        }

        #if DEBUG
        let candidates = debugSearchPaths(for: name, extensions: extensions)
        for url in candidates where FileManager.default.fileExists(atPath: url.path) {
            return try await loadEntity(from: url)
        }
        #endif

        throw ModelLoadError.missingResource(name)
    }

    static func loadEntity(from url: URL) async throws -> Entity {
        do {
            return try await Entity(contentsOf: url)
        } catch {
            throw ModelLoadError.loadFailed("\(url.lastPathComponent): \(error.localizedDescription)")
        }
    }

    /// Collect animation resources under an entity hierarchy.
    static func collectAnimations(from root: Entity) -> [String: AnimationResource] {
        var found: [String: AnimationResource] = [:]

        func visit(_ entity: Entity) {
            for available in entity.availableAnimations {
                let name = available.name?.trimmingCharacters(in: .whitespacesAndNewlines)
                let key = (name?.isEmpty == false ? name! : "anim_\(found.count)")
                if found[key] == nil {
                    found[key] = available
                }
            }
            for child in entity.children {
                visit(child)
            }
        }

        visit(root)
        return found
    }

    static func matchAnimation(
        hints: [String],
        in library: [String: AnimationResource]
    ) -> AnimationResource? {
        if library.isEmpty { return nil }

        let loweredHints = hints.map { $0.lowercased() }

        for (name, resource) in library {
            let lower = name.lowercased()
            if loweredHints.contains(where: { lower == $0 || lower.contains($0) || $0.contains(lower) }) {
                return resource
            }
        }

        // Fallback: first clip
        return library.values.first
    }

    #if DEBUG
    private static func debugSearchPaths(for name: String, extensions: [String]) -> [URL] {
        var urls: [URL] = []
        let fm = FileManager.default
        let cwd = URL(fileURLWithPath: fm.currentDirectoryPath)

        let relativeFolders = [
            "DojoFighterNative/DojoFighter/Resources/Models",
            "DojoFighter/Resources/Models",
            "Resources/Models",
            ".",
            ".."
        ]

        for folder in relativeFolders {
            let base = cwd.appendingPathComponent(folder)
            for ext in extensions {
                urls.append(base.appendingPathComponent("\(name).\(ext)"))
            }
        }

        // Also try absolute workspace paths commonly used in this repo
        let home = fm.homeDirectoryForCurrentUser
        let workspace = home.appendingPathComponent("Development/3d")
        for ext in extensions {
            urls.append(workspace.appendingPathComponent("\(name).\(ext)"))
            urls.append(
                workspace
                    .appendingPathComponent("DojoFighterNative/DojoFighter/Resources/Models")
                    .appendingPathComponent("\(name).\(ext)")
            )
        }

        return urls
    }
    #endif
}

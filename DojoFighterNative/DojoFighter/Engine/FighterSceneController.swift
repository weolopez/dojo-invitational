import Foundation
import RealityKit
import SwiftUI
import Combine
import simd

#if os(macOS)
import AppKit
#endif

@MainActor
final class FighterSceneController: ObservableObject {
    let state = FighterState()
    let cameraRig = CameraRig()
    let combat = CombatSystem()

    private(set) var sceneRoot = Entity()
    private var fighterRoot = Entity()
    private var bagEntity: Entity?
    private var worldAnchor = AnchorEntity(world: .zero)

    private var moveInput = SIMD3<Float>.zero
    private var displayLink: CADisplayLink?
    private var lastTimestamp: CFTimeInterval?
    private var bannerClearTask: Task<Void, Never>?
    private var isLoaded = false

    /// RealityView installs this root once.
    func makeSceneRoot() -> Entity {
        if !isLoaded {
            isLoaded = true
            Task { await loadScene() }
        }
        return worldAnchor
    }

    func loadScene() async {
        state.statusMessage = "Building dojo…"
        worldAnchor.children.removeAll()
        sceneRoot = Entity()
        sceneRoot.name = "DojoRoot"
        worldAnchor.addChild(sceneRoot)

        setupLighting()
        buildProceduralArena()

        // Camera
        let camEntity = cameraRig.camera
        camEntity.name = "FightCamera"
        sceneRoot.addChild(camEntity)

        // Try Blender exports (USDZ preferred)
        state.statusMessage = "Loading Blender fighter…"
        var loadedFighter = false

        do {
            let arena = try await ModelLoader.loadEntity(named: ModelLoader.arenaModelName)
            arena.name = "BlenderArena"
            normalizeModel(arena, targetHeight: 1.85, placeOnGround: true)
            sceneRoot.addChild(arena)
            fighterRoot = findFighterNode(in: arena) ?? arena
            bagEntity = findBagNode(in: arena)
            let anims = ModelLoader.collectAnimations(from: arena)
            combat.attach(fighter: fighterRoot, bag: bagEntity, animations: anims)
            cameraRig.focusEntity = fighterRoot
            state.modelLoaded = true
            state.usingProceduralFallback = false
            state.statusMessage = anims.isEmpty
                ? "Arena loaded · procedural strikes (no clips found)"
                : "Arena loaded · \(anims.count) animation clip(s)"
            loadedFighter = true
        } catch {
            state.statusMessage = "Arena USDZ missing — trying avatar…"
        }

        if !loadedFighter {
            do {
                let avatar = try await ModelLoader.loadEntity(named: ModelLoader.avatarModelName)
                avatar.name = "HyperAvatar"
                normalizeModel(avatar, targetHeight: 1.75, placeOnGround: true)
                sceneRoot.addChild(avatar)
                fighterRoot = avatar
                let anims = ModelLoader.collectAnimations(from: avatar)
                combat.attach(fighter: fighterRoot, bag: bagEntity, animations: anims)
                cameraRig.focusEntity = fighterRoot
                state.modelLoaded = true
                state.usingProceduralFallback = false
                state.statusMessage = "Avatar loaded. Export full arena USDZ for the complete dojo."
                loadedFighter = true
            } catch {
                // Keep procedural fighter
                state.usingProceduralFallback = true
                state.modelLoaded = false
                state.statusMessage = "No USDZ yet — procedural fighter. Run export script."
                let procedural = makeProceduralFighter()
                sceneRoot.addChild(procedural)
                fighterRoot = procedural
                combat.attach(fighter: fighterRoot, bag: bagEntity, animations: [:])
                cameraRig.focusEntity = fighterRoot
            }
        }

        startLoop()
        playMove(.stance)
    }

    // MARK: - Input

    func playMove(_ move: CombatMove) {
        state.activeMove = move
        _ = combat.play(move)
        if move.damage > 0 {
            flashCombo(move.comboLabel)
            combat.strikeImpact()
            state.registerHit(damage: move.damage, label: move.comboLabel)
        } else if move == .victory {
            flashCombo(move.comboLabel)
        }
    }

    func strike() {
        let move = state.activeMove == .stance ? CombatMove.jabCross : state.activeMove
        if state.activeMove == .stance {
            playMove(.jabCross)
        } else {
            flashCombo(move.damage > 0 ? "HEAVY IMPACT!" : move.comboLabel)
            combat.strikeImpact()
            if move.damage > 0 {
                state.registerHit(damage: move.damage * 1.25, label: "HEAVY IMPACT!")
            }
        }
    }

    func setCameraMode(_ mode: CameraMode) {
        state.cameraMode = mode
        cameraRig.setMode(mode)
    }

    func toggleCameraMode() {
        let next: CameraMode = state.cameraMode == .orbit ? .action : .orbit
        setCameraMode(next)
    }

    func setAnimationSpeed(_ speed: Float) {
        state.animationSpeed = speed
        combat.animationSpeed = speed
    }

    func handleOrbit(deltaX: CGFloat, deltaY: CGFloat) {
        cameraRig.orbit(deltaX: Float(deltaX), deltaY: Float(deltaY))
    }

    func handleZoom(delta: CGFloat) {
        cameraRig.zoom(delta: Float(delta) * 0.05)
    }

    #if os(macOS)
    func handleKeyDown(_ key: KeyEquivalent) {
        switch key {
        case "w", "W", .upArrow: moveInput.z = -1
        case "s", "S", .downArrow: moveInput.z = 1
        case "a", "A", .leftArrow: moveInput.x = -1
        case "d", "D", .rightArrow: moveInput.x = 1
        case "1": playMove(.stance)
        case "2": playMove(.jabCross)
        case "3": playMove(.roundhouse)
        case "4": playMove(.uppercut)
        case "5": playMove(.flurry)
        case "6": playMove(.victory)
        case " ": strike()
        case "\t": toggleCameraMode()
        default: break
        }
    }

    func handleKeyUp(_ key: KeyEquivalent) {
        switch key {
        case "w", "W", .upArrow where moveInput.z < 0: moveInput.z = 0
        case "s", "S", .downArrow where moveInput.z > 0: moveInput.z = 0
        case "a", "A", .leftArrow where moveInput.x < 0: moveInput.x = 0
        case "d", "D", .rightArrow where moveInput.x > 0: moveInput.x = 0
        default:
            // Soft clear for letter keys without where binding quirks
            if key.character.lowercased() == "w" || key.character.lowercased() == "s" {
                moveInput.z = 0
            }
            if key.character.lowercased() == "a" || key.character.lowercased() == "d" {
                moveInput.x = 0
            }
        }
    }
    #endif

    func resetMatch() {
        state.resetMatch()
        playMove(.stance)
    }

    // MARK: - Frame loop

    private func startLoop() {
        stopLoop()
        #if os(macOS)
        let link = CADisplayLink(target: TickTarget(owner: self), selector: #selector(TickTarget.tick(_:)))
        link.add(to: .main, forMode: .common)
        displayLink = link
        #else
        let link = CADisplayLink(target: TickTarget(owner: self), selector: #selector(TickTarget.tick(_:)))
        link.add(to: .main, forMode: .common)
        displayLink = link
        #endif
    }

    private func stopLoop() {
        displayLink?.invalidate()
        displayLink = nil
        lastTimestamp = nil
    }

    fileprivate func step(timestamp: CFTimeInterval) {
        let dt: Float
        if let last = lastTimestamp {
            dt = Float(min(1.0 / 20.0, max(1.0 / 240.0, timestamp - last)))
        } else {
            dt = 1.0 / 60.0
        }
        lastTimestamp = timestamp

        var dir = moveInput
        if simd_length(dir) > 1 {
            dir = simd_normalize(dir)
        }
        combat.moveFighter(direction: dir, deltaTime: dt)
        combat.update(deltaTime: dt)
        cameraRig.update(deltaTime: dt)
    }

    // MARK: - Scene construction

    private func setupLighting() {
        let ambient = Entity()
        ambient.components.set(PointLightComponent(color: .white, intensity: 2000, attenuationRadius: 40))
        ambient.position = [0, 5, 0]
        sceneRoot.addChild(ambient)

        let key = Entity()
        key.name = "KeyLight"
        key.components.set(
            SpotLightComponent(
                color: UIColorCompat.warmWhite,
                intensity: 4500,
                innerAngleInDegrees: 20,
                outerAngleInDegrees: 55,
                attenuationRadius: 25
            )
        )
        key.position = [-3.5, 6.0, 4.0]
        key.look(at: [0, 1, 0], from: key.position, relativeTo: nil)
        sceneRoot.addChild(key)

        let rimBlue = Entity()
        rimBlue.components.set(PointLightComponent(color: .systemBlue, intensity: 3500, attenuationRadius: 14))
        rimBlue.position = [-3.8, 3.0, -3.5]
        sceneRoot.addChild(rimBlue)

        let rimRed = Entity()
        rimRed.components.set(PointLightComponent(color: .systemRed, intensity: 3500, attenuationRadius: 14))
        rimRed.position = [3.8, 3.0, -3.2]
        sceneRoot.addChild(rimRed)
    }

    private func buildProceduralArena() {
        // Floor
        let floorMesh = MeshResource.generatePlane(width: 28, depth: 28)
        var floorMat = SimpleMaterial(color: UIColorCompat.floor, isMetallic: false)
        floorMat.roughness = 0.85
        let floor = ModelEntity(mesh: floorMesh, materials: [floorMat])
        floor.name = "DojoFloor"
        floor.position = [0, 0, 0]
        sceneRoot.addChild(floor)

        // Octagon mat (approx with cylinder)
        let matMesh = MeshResource.generateCylinder(height: 0.06, radius: 3.8)
        var matMat = SimpleMaterial(color: UIColorCompat.mat, isMetallic: false)
        matMat.roughness = 0.7
        let octagon = ModelEntity(mesh: matMesh, materials: [matMat])
        octagon.name = "OctagonMat"
        octagon.position = [0, 0.03, 0]
        sceneRoot.addChild(octagon)

        // Neon ring
        let ringMesh = MeshResource.generateBox(size: [7.4, 0.04, 7.4], cornerRadius: 0.02)
        var neon = SimpleMaterial(color: UIColorCompat.neon, isMetallic: false)
        #if os(iOS) || os(macOS)
        // emissive approx via bright color
        #endif
        let ring = ModelEntity(mesh: ringMesh, materials: [neon])
        ring.name = "NeonRing"
        ring.position = [0, 0.06, 0]
        ring.scale = [1, 0.15, 1]
        sceneRoot.addChild(ring)

        // Walls
        addWall(name: "BackWall", position: [0, 2.5, -5.5], size: [12, 5, 0.2])
        addWall(name: "LeftWall", position: [-5.5, 2.5, 0], size: [0.2, 5, 12])
        addWall(name: "RightWall", position: [5.5, 2.5, 0], size: [0.2, 5, 12])

        // Heavy bag
        let bag = makeHeavyBag()
        bag.position = [2.2, 1.2, -1.4]
        sceneRoot.addChild(bag)
        bagEntity = bag
    }

    private func addWall(name: String, position: SIMD3<Float>, size: SIMD3<Float>) {
        let mesh = MeshResource.generateBox(size: size)
        var mat = SimpleMaterial(color: UIColorCompat.wall, isMetallic: false)
        mat.roughness = 0.9
        let wall = ModelEntity(mesh: mesh, materials: [mat])
        wall.name = name
        wall.position = position
        sceneRoot.addChild(wall)
    }

    private func makeHeavyBag() -> ModelEntity {
        let mesh = MeshResource.generateCylinder(height: 1.2, radius: 0.28)
        var mat = SimpleMaterial(color: UIColorCompat.bag, isMetallic: false)
        mat.roughness = 0.4
        let bag = ModelEntity(mesh: mesh, materials: [mat])
        bag.name = "HeavyBag"
        return bag
    }

    private func makeProceduralFighter() -> Entity {
        let root = Entity()
        root.name = "ProceduralFighter"

        let skin = SimpleMaterial(color: UIColorCompat.skin, isMetallic: false)
        let dark = SimpleMaterial(color: UIColorCompat.gear, isMetallic: false)

        let torso = ModelEntity(
            mesh: .generateBox(size: [0.38, 0.55, 0.22], cornerRadius: 0.06),
            materials: [dark]
        )
        torso.position = [0, 1.15, 0]
        root.addChild(torso)

        let head = ModelEntity(mesh: .generateSphere(radius: 0.13), materials: [skin])
        head.position = [0, 1.55, 0]
        root.addChild(head)

        let hips = ModelEntity(
            mesh: .generateBox(size: [0.34, 0.2, 0.2], cornerRadius: 0.04),
            materials: [dark]
        )
        hips.position = [0, 0.82, 0]
        root.addChild(hips)

        for x in [-0.22, 0.22] as [Float] {
            let leg = ModelEntity(
                mesh: .generateBox(size: [0.12, 0.7, 0.14], cornerRadius: 0.04),
                materials: [dark]
            )
            leg.position = [x, 0.4, 0]
            root.addChild(leg)

            let arm = ModelEntity(
                mesh: .generateBox(size: [0.1, 0.55, 0.1], cornerRadius: 0.04),
                materials: [skin]
            )
            arm.position = [x * 1.4, 1.15, 0.05]
            root.addChild(arm)
        }

        return root
    }

    private func normalizeModel(_ entity: Entity, targetHeight: Float, placeOnGround: Bool) {
        entity.position = .zero
        entity.scale = .one

        let bounds = entity.visualBounds(relativeTo: nil)
        let height = bounds.extents.y
        if height > 0.001 {
            let scale = targetHeight / height
            entity.scale = SIMD3<Float>(repeating: scale)
        }

        if placeOnGround {
            let scaledBounds = entity.visualBounds(relativeTo: nil)
            entity.position = [
                -scaledBounds.center.x,
                -scaledBounds.min.y,
                -scaledBounds.center.z
            ]
        }
    }

    private func findFighterNode(in root: Entity) -> Entity? {
        let names = ["Fighter", "Armature", "Player", "Character", "mixamorig", "Body"]
        return findEntity(namedLike: names, in: root) ?? root
    }

    private func findBagNode(in root: Entity) -> Entity? {
        findEntity(namedLike: ["HeavyBag", "Bag", "PunchingBag"], in: root)
    }

    private func findEntity(namedLike candidates: [String], in root: Entity) -> Entity? {
        let lowered = candidates.map { $0.lowercased() }
        var match: Entity?

        func visit(_ entity: Entity) {
            if match != nil { return }
            let n = entity.name.lowercased()
            if lowered.contains(where: { n.contains($0) }) {
                match = entity
                return
            }
            for child in entity.children {
                visit(child)
            }
        }

        visit(root)
        return match
    }

    private func flashCombo(_ text: String) {
        state.comboBanner = text
        bannerClearTask?.cancel()
        bannerClearTask = Task {
            try? await Task.sleep(nanoseconds: 900_000_000)
            guard !Task.isCancelled else { return }
            state.clearBanner()
        }
    }

    deinit {
        displayLink?.invalidate()
    }
}

// CADisplayLink target (NSObject) bridging into the controller
private final class TickTarget: NSObject {
    weak var owner: FighterSceneController?

    init(owner: FighterSceneController) {
        self.owner = owner
    }

    @objc func tick(_ link: CADisplayLink) {
        Task { @MainActor in
            owner?.step(timestamp: link.timestamp)
        }
    }
}

/// Color helpers that compile on macOS + iOS without UIKit-only APIs in macOS-only builds.
enum UIColorCompat {
    #if os(macOS)
    static let warmWhite = NSColor(calibratedRed: 1.0, green: 0.95, blue: 0.88, alpha: 1)
    static let floor = NSColor(calibratedRed: 0.07, green: 0.09, blue: 0.12, alpha: 1)
    static let mat = NSColor(calibratedRed: 0.14, green: 0.17, blue: 0.22, alpha: 1)
    static let neon = NSColor(calibratedRed: 0.2, green: 0.65, blue: 1.0, alpha: 1)
    static let wall = NSColor(calibratedRed: 0.07, green: 0.08, blue: 0.10, alpha: 1)
    static let bag = NSColor(calibratedRed: 0.58, green: 0.09, blue: 0.10, alpha: 1)
    static let skin = NSColor(calibratedRed: 0.76, green: 0.55, blue: 0.44, alpha: 1)
    static let gear = NSColor(calibratedRed: 0.11, green: 0.13, blue: 0.16, alpha: 1)
    #else
    static let warmWhite = UIColor(red: 1.0, green: 0.95, blue: 0.88, alpha: 1)
    static let floor = UIColor(red: 0.07, green: 0.09, blue: 0.12, alpha: 1)
    static let mat = UIColor(red: 0.14, green: 0.17, blue: 0.22, alpha: 1)
    static let neon = UIColor(red: 0.2, green: 0.65, blue: 1.0, alpha: 1)
    static let wall = UIColor(red: 0.07, green: 0.08, blue: 0.10, alpha: 1)
    static let bag = UIColor(red: 0.58, green: 0.09, blue: 0.10, alpha: 1)
    static let skin = UIColor(red: 0.76, green: 0.55, blue: 0.44, alpha: 1)
    static let gear = UIColor(red: 0.11, green: 0.13, blue: 0.16, alpha: 1)
    #endif
}

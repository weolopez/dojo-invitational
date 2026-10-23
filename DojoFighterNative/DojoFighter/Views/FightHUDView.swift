import SwiftUI

struct FightHUDView: View {
    @ObservedObject var controller: FighterSceneController
    @ObservedObject private var state: FighterState

    init(controller: FighterSceneController) {
        self.controller = controller
        self._state = ObservedObject(wrappedValue: controller.state)
    }

    var body: some View {
        ZStack(alignment: .topLeading) {
            VStack(alignment: .leading, spacing: 12) {
                headerCard
                combatCard
                cameraCard
                speedCard
                hintsCard
            }
            .padding(18)
            .frame(maxWidth: 360, alignment: .leading)

            VStack {
                HStack {
                    Spacer()
                    healthStack
                        .padding(.trailing, 20)
                        .padding(.top, 18)
                }
                Spacer()
            }

            if !state.comboBanner.isEmpty {
                VStack {
                    Spacer().frame(height: 28)
                    HStack {
                        Spacer()
                        Text(state.comboBanner)
                            .font(.system(size: 28, weight: .black, design: .rounded))
                            .italic()
                            .foregroundStyle(Color.yellow)
                            .shadow(color: .red.opacity(0.7), radius: 12, y: 4)
                            .padding(.trailing, 28)
                    }
                    Spacer()
                }
                .allowsHitTesting(false)
                .transition(.scale.combined(with: .opacity))
                .animation(.easeOut(duration: 0.15), value: state.comboBanner)
            }
        }
    }

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Text("Dojo Fighter")
                    .font(.headline.weight(.bold))
                Text("NATIVE")
                    .font(.caption2.weight(.bold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color.red)
                    .clipShape(Capsule())
            }
            Text(state.statusMessage)
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .background(cardBackground)
    }

    private var combatCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionTitle("Combat")
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                ForEach(CombatMove.allCases) { move in
                    Button {
                        controller.playMove(move)
                    } label: {
                        Text("\(move.hotkey). \(move.displayName)")
                            .font(.caption.weight(.semibold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                    }
                    .buttonStyle(.plain)
                    .background(state.activeMove == move ? Color.red : Color.white.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(Color.white.opacity(0.12), lineWidth: 1)
                    )
                }
            }

            Button {
                controller.strike()
            } label: {
                Text("SPACE · Heavy Strike")
                    .font(.caption.weight(.bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
            }
            .buttonStyle(.plain)
            .background(Color.red.opacity(0.85))
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
        .padding(14)
        .background(cardBackground)
    }

    private var cameraCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionTitle("Camera")
            HStack(spacing: 8) {
                ForEach(CameraMode.allCases) { mode in
                    Button {
                        controller.setCameraMode(mode)
                    } label: {
                        Text(mode.title)
                            .font(.caption.weight(.semibold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                    }
                    .buttonStyle(.plain)
                    .background(state.cameraMode == mode ? Color.blue : Color.white.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
        }
        .padding(14)
        .background(cardBackground)
    }

    private var speedCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                sectionTitle("Anim Speed")
                Spacer()
                Text(String(format: "%.1fx", state.animationSpeed))
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
            }
            Slider(
                value: Binding(
                    get: { Double(state.animationSpeed) },
                    set: { controller.setAnimationSpeed(Float($0)) }
                ),
                in: 0.2...2.2,
                step: 0.1
            )
            .tint(.red)
        }
        .padding(14)
        .background(cardBackground)
    }

    private var hintsCard: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("WASD footwork · 1–6 moves · Tab camera · drag orbit")
                .font(.caption2)
                .foregroundStyle(.secondary)
            if state.usingProceduralFallback {
                Text("Export USDZ from Blender to load your real model.")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.orange)
            }
            Button("Reset Match") {
                controller.resetMatch()
            }
            .font(.caption.weight(.semibold))
            .buttonStyle(.plain)
            .padding(.top, 4)
        }
        .padding(14)
        .background(cardBackground)
    }

    private var healthStack: some View {
        VStack(alignment: .trailing, spacing: 10) {
            healthBar(title: "YOU", ratio: state.playerHealthRatio, color: .green)
            healthBar(title: "OPP / BAG", ratio: state.opponentHealthRatio, color: .red)
            if state.comboCount > 0 {
                Text("COMBO x\(state.comboCount)")
                    .font(.caption.weight(.black))
                    .foregroundStyle(.yellow)
            }
        }
        .padding(14)
        .background(cardBackground)
    }

    private func healthBar(title: String, ratio: Double, color: Color) -> some View {
        VStack(alignment: .trailing, spacing: 4) {
            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(.secondary)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.1))
                    Capsule()
                        .fill(color)
                        .frame(width: max(8, geo.size.width * ratio))
                }
            }
            .frame(width: 180, height: 10)
        }
    }

    private func sectionTitle(_ text: String) -> some View {
        Text(text.uppercased())
            .font(.caption2.weight(.bold))
            .foregroundStyle(.secondary)
            .tracking(0.6)
    }

    private var cardBackground: some View {
        RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(Color.black.opacity(0.55))
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

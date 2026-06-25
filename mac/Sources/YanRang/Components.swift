import SwiftUI

/*
 * [INPUT]: 依赖 SwiftUI/AppKit、Color 令牌
 * [OUTPUT]: 对外提供 card()/clickable() 修饰器、BreathingDot、StatTile、ConfigRow
 * [POS]: mac/YanRang 复用组件层，承载 shadcn Card/状态点/统计块的原生等价物
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */
import AppKit

// 卡片底座：bg/surface(#fff) + border/default(#e5e5e5)，圆角 radius=10（Figma --radius）
extension View {
    func card(_ radius: CGFloat = 10) -> some View {
        background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(Color.card))
            .overlay(RoundedRectangle(cornerRadius: radius, style: .continuous).stroke(Color.hairline, lineWidth: 1))
    }

    // 可点提示:鼠标移上去变手型指针——所有可点元素统一加它,用户一看便知此处能点。
    // Tahoe(macOS 15+)用原生 pointerStyle(.link);旧系统降级 onHover+NSCursor。
    @ViewBuilder func clickable() -> some View {
        if #available(macOS 15.0, *) {
            self.pointerStyle(.link)
        } else {
            self.onHover { $0 ? NSCursor.pointingHand.push() : NSCursor.pop() }
        }
    }
}

// ============================================================================
//  呼吸灯：聆听=绿色脉冲 / 暂停=灰 / 准备=黄
//  脉冲扩散下沉到 Core Animation(CALayer),在 GPU/CA 层独立循环——
//  关键:SwiftUI 的 repeatForever 动画会驱动整个 NSHostingView 每帧重算整树
//  DisplayList(display-link 60fps),实测持续烧 ~15% CPU。改用 CABasicAnimation 后,
//  动画交给 Core Animation,SwiftUI render 循环彻底静默(静止 CPU 归零)。
// ============================================================================
struct BreathingDot: View {
    let active: Bool
    let muted: Bool
    var body: some View {
        PulseDotRep(active: active, muted: muted).frame(width: 14, height: 14)
    }
}

private struct PulseDotRep: NSViewRepresentable {
    let active: Bool
    let muted: Bool
    func makeNSView(context: Context) -> PulseDotView { PulseDotView() }
    func updateNSView(_ v: PulseDotView, context: Context) { v.apply(active: active, muted: muted) }
}

/// 呼吸灯的 Core Animation 宿主:底圆(实心) + 脉冲圆(CABasicAnimation scale/opacity 无限循环)。
final class PulseDotView: NSView {
    private let pulse = CALayer()                       // 扩散脉冲(在下)
    private let base  = CALayer()                       // 实心圆点(在上,盖住脉冲起点)
    private var animating = false
    private var curActive = false
    private var curMuted = false

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        layer = CALayer()
        let d: CGFloat = 14
        for l in [pulse, base] {                        // 先加 pulse(底层) 后加 base(上层)
            l.frame = CGRect(x: 0, y: 0, width: d, height: d)
            l.cornerRadius = d / 2
            layer?.addSublayer(l)
        }
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) 未实现") }

    override var intrinsicContentSize: NSSize { NSSize(width: 14, height: 14) }

    // CALayer 颜色非 appearance-dynamic,明暗切换需手动重上色。
    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        applyColors()
    }

    func apply(active: Bool, muted: Bool) {
        curActive = active; curMuted = muted
        applyColors()
        if active && !animating { startPulse() }
        else if !active && animating { stopPulse() }
    }

    private var isDark: Bool { effectiveAppearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua }

    private func applyColors() {
        let ok = NSColor(hex: isDark ? "22c55e" : "16a34a").cgColor
        base.backgroundColor = curActive ? ok
            : (curMuted ? NSColor(hex: "737373").cgColor
                        : NSColor(hex: isDark ? "f59e0b" : "d97706").cgColor)
        pulse.backgroundColor = ok
        pulse.isHidden = !curActive
    }

    private func startPulse() {
        animating = true
        let scale = CABasicAnimation(keyPath: "transform.scale")
        scale.fromValue = 1.0; scale.toValue = 1.9
        let fade = CABasicAnimation(keyPath: "opacity")
        fade.fromValue = 0.55; fade.toValue = 0.0
        let group = CAAnimationGroup()
        group.animations = [scale, fade]
        group.duration = 1.5
        group.timingFunction = CAMediaTimingFunction(name: .easeOut)
        group.repeatCount = .infinity
        group.isRemovedOnCompletion = false
        pulse.add(group, forKey: "breathe")
    }

    private func stopPulse() {
        animating = false
        pulse.removeAnimation(forKey: "breathe")
    }
}

// 大数字统计块
struct StatTile: View {
    let value: String
    let label: String
    let accent: Bool
    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(value)
                .font(.system(size: 38, weight: .semibold))
                .monospacedDigit()
                .foregroundStyle(accent ? Color.brand : Color.appFg)
            Text(label).font(.system(size: 13)).foregroundStyle(Color.textTertiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .card()
    }
}

// 配置项状态：配好=绿勾 / 未配=红叉
struct ConfigRow: View {
    let ok: Bool
    let label: String
    let detail: String
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.system(size: 15))
                .foregroundStyle(ok ? Color.ok : Color.danger)
            Text(label).font(.system(size: 14, weight: .medium))
            Text(detail)
                .font(.system(size: 14))
                .foregroundStyle(ok ? Color.textSecondary : Color.danger)
                .lineLimit(1).truncationMode(.middle)
            Spacer(minLength: 0)
        }
    }
}

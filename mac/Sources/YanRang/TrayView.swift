import SwiftUI
import AppKit

/// 菜单栏托盘弹窗(MenuBarExtra .window)。共享同一 engine → 暂停与主窗口实时同步。
/// 原生可上色：🌐 主页(柔和红) / 🪨 资料库(柔和紫) / 🐱 GitHub(柔和蓝)。
struct TrayView: View {
    @EnvironmentObject var engine: Engine
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        VStack(alignment: .leading, spacing: 1) {
            Row(icon: engine.muted ? "play.fill" : "pause.fill",
                title: engine.muted ? "继续录音" : "暂停录音") { engine.toggleMuted() }
            Row(icon: "house", title: "打开主窗口") {
                openWindow(id: "main")
                NSApp.activate(ignoringOtherApps: true)
            }

            Divider().padding(.vertical, 4)
            Text("言壤 v\(engine.version)")
                .font(.caption).foregroundStyle(.tertiary)
                .padding(.horizontal, 10).padding(.vertical, 2)
            Divider().padding(.vertical, 4)

            Row(emoji: "🌐", title: "作者主页 · zhaozimin.cn", color: .softRed) { open("https://zhaozimin.cn") }
            Row(emoji: "🪨", title: "Obsidian 资料库 · guangtou.me", color: .softPurple) { open("https://guangtou.me") }
            Row(emoji: "🐱", title: "GitHub · zhaozimin", color: .softBlue) { open("https://github.com/zhaozimin") }

            Divider().padding(.vertical, 4)
            Row(icon: "power", title: "退出言壤") { NSApplication.shared.terminate(nil) }
        }
        .padding(8)
        .frame(width: 310)   // 加宽：Obsidian 资料库·guangtou.me 单行不折行
    }

    private func open(_ s: String) { if let u = URL(string: s) { NSWorkspace.shared.open(u) } }
}

#Preview {
    @Previewable @StateObject var engine = Engine()
    TrayView()
        .environmentObject(engine)
        .frame(width: 310, height: 280)
}

#Preview {
    TrayView()
        .environmentObject(Engine())
        .frame(width: 310, height: 280)
}

private struct Row: View {
    var icon: String? = nil
    var emoji: String? = nil
    let title: String
    var color: Color? = nil
    let action: () -> Void
    @State private var hover = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 9) {
                if let emoji { Text(emoji).frame(width: 18) }
                else if let icon { Image(systemName: icon).frame(width: 18).foregroundStyle(color ?? .primary) }
                Text(title).foregroundStyle(color ?? .primary).lineLimit(1).fixedSize()
                Spacer(minLength: 0)
            }
            .font(.system(size: 13, weight: .medium))
            .padding(.horizontal, 8).padding(.vertical, 6)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 6, style: .continuous).fill(hover ? Color.primary.opacity(0.08) : .clear))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hover = $0 }
    }
}

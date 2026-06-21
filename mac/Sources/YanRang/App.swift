import SwiftUI
import AppKit

/*
 * [INPUT]: 依赖 Engine、各页面 View、Color 令牌、Asset.trayIcon
 * [OUTPUT]: 对外 public YanRangApp(由 Sources/YanRangApp/main.swift 启动)、统一工具栏 RootView、分段导航 Segmented、状态丸 StatusPill
 * [POS]: YanRangUI 库的外壳层，1:1 复刻 desktop/src/App.tsx 的「标题栏合一」布局；入口下沉到库以放行 SwiftUI 预览
 * [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
 */

// @main 不在此处：代码沉到库 target(YanRangUI) 以放行预览，启动改由可执行 target 的 main.swift 调 YanRangApp.main()。
public struct YanRangApp: App {
    public init() {}
    @StateObject private var engine = Engine()

    public var body: some Scene {
        // 主窗口：标题设空(根治切页时系统重画出第二个「言壤」的竞态——无文字可渲染)；
        // 原生统一工具栏 → 红绿灯与工具栏项同行；隐藏工具栏背景/分割线 + 窗口底色=页面底色 → 上下一体。
        // app 菜单名由 Info.plist 的 CFBundleName=言壤 提供，不受影响。
        Window("", id: "main") {
            RootView().environmentObject(engine)
        }
        .windowToolbarStyle(.unified)   // 更高的统一工具栏，容纳放大的导航 + 居中红绿灯
        .defaultSize(width: 1000, height: 700)

        // 菜单栏托盘：真 logo(模板图标) + 自定义弹窗(文字可彩色)
        MenuBarExtra {
            TrayView().environmentObject(engine)
        } label: {
            Image(nsImage: Asset.trayIcon)
        }
        .menuBarExtraStyle(.window)
    }
}

// ============================================================================
//  四个页面
// ============================================================================
enum Page: CaseIterable, Identifiable {
    case home, history, settings, about
    var id: Self { self }
    var title: String {
        switch self {
        case .home: "首页"; case .history: "历史"; case .settings: "设置"; case .about: "关于"
        }
    }
    var icon: String {
        switch self {
        case .home: "house"; case .history: "calendar"; case .settings: "gearshape"; case .about: "info.circle"
        }
    }
}

struct RootView: View {
    @EnvironmentObject var engine: Engine
    @State private var page: Page = .home

    var body: some View {
        Group {
            switch page {
            case .home: HomeView()
            case .history: HistoryView()
            case .settings: SettingsView()
            case .about: AboutView()
            }
        }
        .frame(minWidth: 880, minHeight: 600)
        .background(Color.appBg)
        .background(WindowConfigurator())                 // 窗口底色=appBg，消除工具栏接缝
        .toolbar {
            // 三项统一隐藏 Tahoe「共享液态玻璃」底：系统会给每个 ToolbarItem 套一层胶囊玻璃，
            // 与自绘容器圆角不重合 → 视觉「框中框」。.toolbarBackground(.hidden) 只去整条工具栏底，去不掉 per-item 这层。
            //
            // 切页右移根因：.principal 在底层=NSToolbar centeredItem，在「左右两组之间」居中而非窗口居中。
            // 左侧=红绿灯(~78)+品牌，右侧仅状态丸 → 两组间中点相对窗口右偏 → 重排时跳过去。
            // 修法：给右侧补一段透明占位(BalancedStatus)，把「两组间中点」拉回窗口几何中心 → 不再跳。
            if #available(macOS 26.0, *) {
                ToolbarItem(placement: .navigation)    { BrandTitle() }.sharedBackgroundVisibility(.hidden)
                ToolbarItem(placement: .principal)     { Segmented(page: $page) }.sharedBackgroundVisibility(.hidden)
                ToolbarItem(placement: .primaryAction) { BalancedStatus() }.sharedBackgroundVisibility(.hidden)
            } else {
                ToolbarItem(placement: .navigation)    { BrandTitle() }
                ToolbarItem(placement: .principal)     { Segmented(page: $page) }
                ToolbarItem(placement: .primaryAction) { BalancedStatus() }
            }
        }
        .toolbarBackground(.hidden, for: .windowToolbar)   // 去背景=去分割线
    }
}

// 配置窗口：①底色=appBg 消接缝 ②清空系统标题 ③把红绿灯垂直居中到标题栏中线。
// 居中需在布局完成后做，且监听 resize 重做，防止被 AppKit 复位。
private struct WindowConfigurator: NSViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }
    func makeNSView(context: Context) -> NSView {
        let v = NSView()
        DispatchQueue.main.async { context.coordinator.attach(v.window) }
        return v
    }
    func updateNSView(_ v: NSView, context: Context) {
        DispatchQueue.main.async { context.coordinator.attach(v.window) }
    }

    final class Coordinator {
        private weak var window: NSWindow?
        private var observer: NSObjectProtocol?

        func attach(_ w: NSWindow?) {
            guard let w else { return }
            harden(w)                 // 每次更新都做(幂等)：防 SwiftUI 切页时把标题复位成「言壤」
            centerTrafficLights()
            guard w !== window else { return }   // —— 以下仅在窗口首次出现/被更换时做一次 ——
            if let o = observer { NotificationCenter.default.removeObserver(o); observer = nil }
            window = w
            observer = NotificationCenter.default.addObserver(    // 重绑到新窗口(旧窗口关闭→托盘重开会换实例)
                forName: NSWindow.didResizeNotification, object: w, queue: .main
            ) { [weak self] _ in self?.centerTrafficLights() }
            // 布局可能晚于此刻完成 → 多次延迟补做(每窗口仅排一次，避免每次刷新无谓堆积)
            for d in [0.05, 0.2, 0.5, 1.0] {
                DispatchQueue.main.asyncAfter(deadline: .now() + d) { [weak self] in self?.centerTrafficLights() }
            }
        }

        // 幂等的窗口外观强制：隐藏系统标题、透明标题栏、底色=appBg
        private func harden(_ w: NSWindow) {
            w.titleVisibility = .hidden
            w.title = ""
            w.titlebarAppearsTransparent = true
            w.backgroundColor = NSColor(name: nil) { ap in
                ap.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua ? NSColor(hex: "0a0a0a") : NSColor(hex: "fafafa")
            }
        }

        deinit { if let o = observer { NotificationCenter.default.removeObserver(o) } }

        private func centerTrafficLights() {
            guard let w = window else { return }
            for type in [NSWindow.ButtonType.closeButton, .miniaturizeButton, .zoomButton] {
                guard let b = w.standardWindowButton(type), let sv = b.superview else { continue }
                var f = b.frame
                f.origin.y = (sv.bounds.height - f.height) / 2   // 居中到整条标题栏高度
                b.setFrameOrigin(f.origin)
            }
        }
    }
}

// 品牌：言壤. + 版本（工具栏左侧，紧随红绿灯）
private struct BrandTitle: View {
    @EnvironmentObject var engine: Engine
    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 0) {
            Text("言壤").font(.system(size: 15, weight: .semibold))
            Text(".").font(.system(size: 15, weight: .semibold)).foregroundStyle(Color.brand)
            Text("v\(engine.version)").font(.system(size: 12))
                .foregroundStyle(Color.textTertiary).padding(.leading, 6)
        }
    }
}

// 分段导航胶囊（bg/sunken 容器 + 选中 bg/surface + 阴影）
private struct Segmented: View {
    @Binding var page: Page
    var body: some View {
        HStack(spacing: 2) {
            ForEach(Page.allCases) { p in SegItem(p: p, page: $page) }
        }
        .padding(3)
        .background(RoundedRectangle(cornerRadius: 9, style: .continuous).fill(Color.sunken))
        .fixedSize()   // 防止工具栏压缩导致「首页」被截成「...」
    }
}

private struct SegItem: View {
    let p: Page
    @Binding var page: Page
    @State private var hover = false
    private var active: Bool { page == p }

    var body: some View {
        Button { page = p } label: {
            HStack(spacing: 6) {
                Image(systemName: p.icon).font(.system(size: 13, weight: .medium))
                Text(p.title).font(.system(size: 14, weight: .medium))
            }
            .padding(.horizontal, 14).padding(.vertical, 6)
            .fixedSize()
            .foregroundStyle(active || hover ? Color.appFg : Color.textTertiary)
            .background(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(active ? Color.card : .clear)
                    .shadow(color: active ? .black.opacity(0.12) : .clear, radius: 1, y: 1)
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hover = $0 }
    }
}

// 状态丸 + 左侧透明配平：抵消左侧(红绿灯~78 + 品牌~75)与右侧(状态丸~80)的不对称，
// 使 .principal「两组间居中」== 窗口几何居中 → 切页重排不再右移。
// navBalance ≈ 红绿灯 + 品牌 − 状态丸 ≈ 72；肉眼微调(偏左减小、偏右加大)。透明占位贴右端不可见。
private struct BalancedStatus: View {
    static let navBalance: CGFloat = 72
    var body: some View {
        HStack(spacing: 0) {
            Color.clear.frame(width: BalancedStatus.navBalance)
            StatusPill()
        }
        .fixedSize()
    }
}

// 状态丸：圆角胶囊 + 彩色圆点 + 文字（聆听中/已暂停/准备中）
struct StatusPill: View {
    @EnvironmentObject var engine: Engine
    private var color: Color { engine.listening ? .ok : (engine.muted ? Color.textTertiary : .warn) }
    var body: some View {
        HStack(spacing: 6) {
            Circle().fill(color).frame(width: 9, height: 9)
            Text(engine.muted ? "已暂停" : engine.listening ? "聆听中" : "准备中")
                .font(.system(size: 13, weight: .medium))
        }
        .padding(.horizontal, 12).padding(.vertical, 6)
        // 同心：半径=窗口外角(16) − 内缩(≈8) = 8pt continuous。放弃满胶囊——胶囊半径=高/2 是自适应，
        // 不知道窗口外角是 16，丸高一变就漂、永远凑不出同心。显式钉死半径，同心是设计出来的。
        .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.card))
        .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(Color.hairline, lineWidth: 1))
        .fixedSize()
    }
}

#Preview("首页") {
    @Previewable @StateObject var engine = Engine()
    HomeView()
        .environmentObject(engine)
        .frame(width: 1000, height: 700)
}

#Preview("完整导航") {
    @Previewable @StateObject var engine = Engine()
    RootView()
        .environmentObject(engine)
        .frame(width: 1000, height: 700)
}

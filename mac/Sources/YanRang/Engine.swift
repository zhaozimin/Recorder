import Foundation
import SwiftUI

struct LogLine: Identifiable {
    let id = UUID()
    let time: String
    let text: String
}

/// 统一的日期键：钉死公历 + en_US_POSIX + 本地时区，避免随系统区域(佛历/和历)漂移。
/// Engine / CalendarView / HistoryView 三处共用此实现，保证键空间同构(否则日历红点失配)。
func ymdKey(_ d: Date) -> String {
    let f = DateFormatter()
    f.calendar = Calendar(identifier: .gregorian)
    f.locale = Locale(identifier: "en_US_POSIX")
    f.timeZone = .current
    f.dateFormat = "yyyy-MM-dd"
    return f.string(from: d)
}

/// UI↔引擎契约。Phase 1：mock。Phase 2：换成读 Python sidecar 的 state.json / vault 文件。
@MainActor
final class Engine: ObservableObject {
    @Published var muted = false
    @Published var live = true
    @Published var count = 23
    @Published var dropped = 6
    @Published var modelReady = true
    @Published var modelName = "whisper-mlx-turbo"
    @Published var enrolled = true
    @Published var speakerOn = true
    @Published var lastScore: Double? = 0.62
    @Published var vault = "/Users/zhao/Desktop/言壤语音日志"
    @Published var updateLatest: String? = "0.9.6"
    let version = "0.9.5"

    var listening: Bool { !muted && live }
    func toggleMuted() { muted.toggle() }

    // ---------------- mock 今日实时流 ----------------
    let today: [LogLine] = [
        .init(time: "08:12", text: "早上好，今天先把录音 App 的设置页过一遍。"),
        .init(time: "08:40", text: "灵感：历史记录用日历来选日期，比纯列表直观多了。"),
        .init(time: "09:15", text: "提醒自己中午之前回复合作方的邮件。"),
        .init(time: "10:03", text: "设置分成五个标签页：语言时区、保存位置、关键词、参数、配置文件。"),
        .init(time: "10:48", text: "关于页直接把作者主页、资料库、GitHub 三个链接写清楚。"),
        .init(time: "11:22", text: "品牌色就用这个红，主操作实心、危险动作用红字。"),
        .init(time: "11:55", text: "记得把周四的复盘提纲发给团队。"),
    ]

    // ---------------- mock 历史 ----------------
    // 用计算属性而非 lazy：常驻 App 跨午夜后「今天」会变，lazy 会把日期键冻结在初始化那天。
    private var history: [String: [LogLine]] {
        let cal = Calendar.current
        func day(_ n: Int) -> String { ymdKey(cal.date(byAdding: .day, value: -n, to: Date())!) }
        return [
            day(0): today,
            day(1): [
                .init(time: "09:30", text: "昨天主要在调试声纹门，短句容易被误判，已加豁免时长。"),
                .init(time: "14:10", text: "把默认保存位置改成了桌面，用户更容易找到。"),
                .init(time: "19:45", text: "晚上读了点关于本地优先软件的文章，很有共鸣。"),
            ],
            day(2): [
                .init(time: "08:05", text: "前天：模型下载走 GitHub Release，国内可达。"),
                .init(time: "16:20", text: "自动更新三关校验跑通了：签名 + 公证 + TeamID。"),
            ],
            day(5): [.init(time: "10:00", text: "五天前：开始构思完整版的桌面窗口。")],
        ]
    }

    func lines(for date: Date) -> [LogLine] { history[ymdKey(date)] ?? [] }

    /// 有记录的日子（"yyyy-MM-dd"）——日历标红点用。
    func historyDates() -> Set<String> { Set(history.keys) }

    func search(_ q: String) -> [(date: String, lines: [LogLine])] {
        let t = q.trimmingCharacters(in: .whitespaces)
        guard !t.isEmpty else { return [] }
        return history.keys.sorted(by: >).compactMap { d in
            let hits = history[d]!.filter { $0.text.contains(t) }
            return hits.isEmpty ? nil : (d, hits)
        }
    }
}

"""Authored fixture data. Hidden setup is never served as a player payload."""

VERSION = "handover-letter-v1"
DEADLINE = 6
ROOMS = {
    "hall": {"name": "大厅", "description": "长桌上的座钟静静走着。交接会即将开始，你需要找到信件，将它带回这里。", "neighbors": ["study", "courtyard"]},
    "study": {"name": "书房", "description": "一间安静的书房。靠窗的书桌有一只可以打开的抽屉。", "neighbors": ["hall"]},
    "courtyard": {"name": "庭院", "description": "石阶通向一处僻静的庭院。从这里看不到大厅和书房里的活动。", "neighbors": ["hall"]},
}
PEOPLE = {"A": "你 · 周砚", "B": "林舟", "C": "许宁"}
INTRODUCTION = "交接会将在六个行动节拍后开始。一封封口的交接信尚未送到长桌上。你受托找到它，并在会议开始前带回大厅。屋里还有两个人，各自忙着手头的事。"
BRIEFING = [
    "你叫周砚，受托将交接信带到大厅。你记得它是一只带有蓝色封口的信封，里面的内容并未向你公开。",
    "开始时，你和林舟在大厅。你知道许宁被安排照看庭院，但这不代表你能一直知道她的位置。",
    "大厅连接书房与庭院。每次提交行动推进一个节拍，查看资料不会耗时。你有六个行动节拍。",
    "你的目标：找到信件，拿到它，并回到大厅。你可以选择路线和观察方式。",
]
OUTCOMES = {
    "delivered": {"title": "如期交接", "text": "会议开始时，你已带着交接信回到大厅。信封仍然封着；你完成了受托的交接。"},
    "incomplete": {"title": "只差一步", "text": "会议开始了。你已经找到信件的线索，或已经拿到信件，但尚未完成大厅的交接。"},
    "not_found": {"title": "未解的去向", "text": "会议开始时，你还没有找到信件。那些没有亲眼见到的经历，仍然是你不知道的部分。"},
}

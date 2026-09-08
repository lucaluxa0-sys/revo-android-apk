package hive

import (
	. "github.com/nosyliam/revolution/pkg/control/actions"
)

var ClaimHiveImage = ImageSteps{
	SelectCoordinate(Change,
		Add(S[int]("honeyOffsetX"), 110), 0,
		Add(S[int]("honeyOffsetX"), 500), Add(S[int]("honeyOffsetY"), 23),
	),
	Variance(1),
	Direction(0),
	Search("claimhive").Find(),
}

var SendTradeImage = ImageSteps{
	SelectCoordinate(Change,
		Add(S[int]("honeyOffsetX"), 110), 0,
		Add(S[int]("honeyOffsetX"), 500), Add(S[int]("honeyOffsetY"), 23),
	),
	Variance(1),
	Direction(0),
	Search("sendtrade").Find(),
}

var TradeDisabledImage = ImageSteps{
	SelectCoordinate(Change,
		Add(S[int]("honeyOffsetX"), 110), 0,
		Add(S[int]("honeyOffsetX"), 500), Add(S[int]("honeyOffsetY"), 23),
	),
	Variance(1),
	Direction(0),
	Search("tradedisabled").Find(),
}

var TradeLockedImage = ImageSteps{
	SelectCoordinate(Change,
		Add(S[int]("honeyOffsetX"), 110), 0,
		Add(S[int]("honeyOffsetX"), 500), Add(S[int]("honeyOffsetY"), 23),
	),
	Variance(1),
	Direction(0),
	Search("tradelocked").Find(),
}

var AllHiveImages = ImageSteps{
	SelectCoordinate(Change,
		Add(S[int]("honeyOffsetX"), 110), 0,
		Add(S[int]("honeyOffsetX"), 600), Add(S[int]("honeyOffsetY"), 23),
	),
	Variance(0),
	Direction(0),
	Search("claimhive", "sendtrade", "tradelocked", "tradedisabled").Find(),
}

var PressEImage = ImageSteps{
	SelectCoordinate(Change,
		Add(S[int]("honeyOffsetX"), 110), 0,
		Add(S[int]("honeyOffsetX"), 600), Add(S[int]("honeyOffsetY"), 23),
	),
	Variance(0),
	Direction(0),
	Search("press_e").Find(),
}

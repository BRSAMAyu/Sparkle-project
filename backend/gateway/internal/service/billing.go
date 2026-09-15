package service

type CostCalculator struct {
	InputPrice  float64 // per 1M tokens
	OutputPrice float64 // per 1M tokens
}

func NewCostCalculator() *CostCalculator {
	// Defaults for GPT-4o-mini (Input $0.15/1M, Output $0.60/1M)
	return &CostCalculator{
		InputPrice:  0.15,
		OutputPrice: 0.60,
	}
}

func (c *CostCalculator) CalculateSavings(cachedResponse string) float64 {
	// Estimate Token count (Rough calculation: 1 Chinese character/Word ≈ 1.5 tokens)
	// In industrial implementation, this should be stored from previous token usage
	tokens := float64(len(cachedResponse)) * 1.5

	// Saved cost = Input(Assume average 50) + Output
	cost := ((50 * c.InputPrice) + (tokens * c.OutputPrice)) / 1000000
	return cost
}
package service

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNewCostCalculator_Defaults(t *testing.T) {
	calc := NewCostCalculator()
	assert.Equal(t, 0.15, calc.InputPrice)
	assert.Equal(t, 0.60, calc.OutputPrice)
}

func TestCalculateSavings_EmptyResponse(t *testing.T) {
	calc := NewCostCalculator()
	savings := calc.CalculateSavings("")
	// Even empty response has input cost: (50 * 0.15) / 1M
	expected := (50 * 0.15) / 1000000
	assert.InDelta(t, expected, savings, 0.0000001)
}

func TestCalculateSavings_NonEmptyResponse(t *testing.T) {
	calc := NewCostCalculator()
	// 100 characters * 1.5 tokens = 150 output tokens
	response := strings.Repeat("a", 100)
	savings := calc.CalculateSavings(response)
	expected := ((50 * 0.15) + (150 * 0.60)) / 1000000
	assert.InDelta(t, expected, savings, 0.0000001)
}

func TestCalculateSavings_CustomPrices(t *testing.T) {
	calc := &CostCalculator{InputPrice: 1.0, OutputPrice: 2.0}
	savings := calc.CalculateSavings("hello")
	// 5 chars * 1.5 = 7.5 tokens
	expected := ((50 * 1.0) + (7.5 * 2.0)) / 1000000
	assert.InDelta(t, expected, savings, 0.0000001)
}

func TestCalculateSavings_LargeResponse(t *testing.T) {
	calc := NewCostCalculator()
	largeResponse := make([]byte, 10000)
	for i := range largeResponse {
		largeResponse[i] = 'x'
	}
	savings := calc.CalculateSavings(string(largeResponse))
	assert.True(t, savings > 0, "savings should be positive for large response")
	// 10000 chars * 1.5 tokens * $0.60/1M / 1M + 50 * $0.15/1M / 1M
	expected := ((50 * 0.15) + (15000 * 0.60)) / 1000000
	assert.InDelta(t, expected, savings, 0.0001)
}

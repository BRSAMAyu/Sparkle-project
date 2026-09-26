package service

// B-06 审计面二观察收口：entitlement 判级 Python/Go 受控双实现跨语言等价测试（网关侧）。
//
// 双实现注释互认（V3-FIX-02 / D17 冻结决策）：本文件 IsProEntitlement /
// IsProEntitlementEffective ↔ 引擎 app/core/entitlement.py
// normalize_entitlement / entitlement_effective（见 user_context.go 注释锚点；
// 审计面：v3/06_agent_fleet/B06_ENTITY_TRUTH_BASELINE.md §2.2-4）。
//
// 等价测试设计（方案 a）：测试向量单源 JSON、双端测试各自消费——同一输入集
// （值域典型值/大小写/空白边界/值域外非法值/到期与边界时刻）分别喂两端判级
// 函数，断言输出全等：
//
//	backend/tests/fixtures/entitlement_tier_vectors.json
//	  └── cases  双端共享（本测试 + backend/tests/unit/test_b06_entitlement_tier_parity.py）
//
// python_only_cases（假值坍缩/注入钟边界/tz 归一）Go 调用面不存在，不在此消费，
// 清单见向量文件 contract.sections。两侧判级语义任一改动必须同卡同步另一侧并
// 更新向量文件（任一侧红即漂移报警，值集/边界行为漂移从此有门）。
//
// 注：本测试以相对路径读包目录外的共享向量（go test 固定以包目录为 cwd），
// 与引擎侧同文件单源，不设 testdata 双拷贝。
import (
	"encoding/json"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
)

const entitlementTierVectorPath = "../../../../backend/tests/fixtures/entitlement_tier_vectors.json"

type tierVectorCase struct {
	ID                string  `json:"id"`
	Raw               string  `json:"raw"`
	ExpiresAt         *string `json:"expires_at"` // null = 永久（pgtype Timestamp Valid=false）
	ExpectedNoExpiry  string  `json:"expected_no_expiry"`
	ExpectedEffective string  `json:"expected_effective"`
	Note              string  `json:"note"`
}

type tierVectorFile struct {
	Cases []tierVectorCase `json:"cases"`
}

func loadEntitlementTierVectors(t *testing.T) tierVectorFile {
	t.Helper()
	raw, err := os.ReadFile(entitlementTierVectorPath)
	if err != nil {
		t.Fatalf("read entitlement tier vectors %s: %v", entitlementTierVectorPath, err)
	}
	var vectors tierVectorFile
	if err := json.Unmarshal(raw, &vectors); err != nil {
		t.Fatalf("parse entitlement tier vectors: %v", err)
	}
	if len(vectors.Cases) == 0 {
		t.Fatal("entitlement tier vectors: empty cases")
	}
	return vectors
}

// TestEntitlementTierParityVectors 共享向量双面断言：
//   - 无 expiry 面：expected_no_expiry=='pro' ⟺ IsProEntitlement（⟺ 引擎 normalize_entitlement）
//   - 到期面：expected_effective=='pro' ⟺ IsProEntitlementEffective（⟺ 引擎 entitlement_effective）
func TestEntitlementTierParityVectors(t *testing.T) {
	vectors := loadEntitlementTierVectors(t)
	for _, tc := range vectors.Cases {
		tc := tc
		t.Run(tc.ID, func(t *testing.T) {
			wantNoExpiry := tc.ExpectedNoExpiry == "pro"
			if got := IsProEntitlement(tc.Raw); got != wantNoExpiry {
				t.Fatalf("IsProEntitlement(%q) = %v, want %v (%s)",
					tc.Raw, got, wantNoExpiry, tc.Note)
			}

			expiresAt := pgtype.Timestamp{Valid: false}
			if tc.ExpiresAt != nil {
				parsed, err := time.Parse(time.RFC3339, *tc.ExpiresAt)
				if err != nil {
					t.Fatalf("case %s: parse expires_at %q: %v", tc.ID, *tc.ExpiresAt, err)
				}
				expiresAt = pgtype.Timestamp{Time: parsed, Valid: true}
			}
			wantEffective := tc.ExpectedEffective == "pro"
			if got := IsProEntitlementEffective(tc.Raw, expiresAt); got != wantEffective {
				t.Fatalf("IsProEntitlementEffective(%q, valid=%v) = %v, want %v (%s)",
					tc.Raw, expiresAt.Valid, got, wantEffective, tc.Note)
			}
		})
	}
}

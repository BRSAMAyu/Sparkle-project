// V3-FIX-271：PhotonTransactionType 三值漂移端上消费面（台账 271）。
//
// 后端真源 app/models/shop.py PhotonTransactionType 十五值；mobile 旧镜像仅十二
// 值，缺 grant_bonus（PHOTON-STREAM combo 加成补录审计流水）、contract_escrow
// （MINT-FIX 契约押金托管预扣）、guest_seed（MINT-FIX 访客体验种子——每个访客
// 首启播种即写 auth.py:978-1001，触达面最宽）。photons.py:63 GET
// /photons/transactions 原样下发 ledger 行，mobile $enumDecode 硬解码无兜底，
// 交易历史遇任一缺失值即 ArgumentError（行内 D-COMM-2 注释自证同型崩溃先例）。
//
// 修复范式（V3-FIX-260 判例）：补三值 + @JsonValue('unknown') 哨兵 +
// @JsonKey(unknownEnumValue) 兜底 + 消费面穷举 switch 补 case + l10n 标签。
//
// 修复前实录（红）：三值/未知值解析抛 ArgumentError。
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

Map<String, dynamic> _transactionJson(String type) => <String, dynamic>{
      'id': 't1',
      'transaction_type': type,
      'amount': 10,
      'balance_before': 100,
      'balance_after': 110,
      'created_at': '2026-09-25T10:00:00Z',
    };

void main() {
  group('V3-FIX-271 PhotonTransactionType wire decode', () {
    test('grant_bonus 值串精确对齐可解析（PHOTON-STREAM 审计流水）', () {
      final tx = PhotonTransaction.fromJson(_transactionJson('grant_bonus'));
      expect(tx.transactionType, PhotonTransactionType.grantBonus);
      expect(tx.isIncome, isTrue);
    });

    test('contract_escrow 值串精确对齐可解析（MINT-FIX 押金托管）', () {
      final tx = PhotonTransaction.fromJson(
        _transactionJson('contract_escrow'),
      );
      expect(tx.transactionType, PhotonTransactionType.contractEscrow);
    });

    test('guest_seed 值串精确对齐可解析（访客首启播种即写、触达面最宽）', () {
      final tx = PhotonTransaction.fromJson(_transactionJson('guest_seed'));
      expect(tx.transactionType, PhotonTransactionType.guestSeed);
    });

    test('未知交易类型降级 unknown 哨兵不崩', () {
      final tx = PhotonTransaction.fromJson(
        _transactionJson('quantum_dividend'),
      );
      expect(tx.transactionType, PhotonTransactionType.unknown);
    });

    test('既有 12 值解析行为保持不变', () {
      expect(
        PhotonTransaction.fromJson(_transactionJson('grant_achievement'))
            .transactionType,
        PhotonTransactionType.grantAchievement,
      );
      expect(
        PhotonTransaction.fromJson(_transactionJson('redeem_pro'))
            .transactionType,
        PhotonTransactionType.redeemPro,
      );
    });

    test('流水列表整表面：含三缺失值与未知值混合行全表可解析', () {
      final rows = <Map<String, dynamic>>[
        _transactionJson('grant_bonus'),
        _transactionJson('contract_escrow'),
        _transactionJson('guest_seed'),
        _transactionJson('purchase'),
        _transactionJson('mystery_future_type'),
      ].map(PhotonTransaction.fromJson).toList();

      expect(rows, hasLength(5));
      expect(rows[0].transactionType, PhotonTransactionType.grantBonus);
      expect(rows[1].transactionType, PhotonTransactionType.contractEscrow);
      expect(rows[2].transactionType, PhotonTransactionType.guestSeed);
      expect(rows[3].transactionType, PhotonTransactionType.purchase);
      expect(rows[4].transactionType, PhotonTransactionType.unknown);
    });

    test('新值消费面标签非空（I18nService zh 回退可取）', () {
      String name(String type) =>
          PhotonTransaction.fromJson(_transactionJson(type))
              .transactionTypeName;
      expect(name('grant_bonus'), isNotEmpty);
      expect(name('contract_escrow'), isNotEmpty);
      expect(name('guest_seed'), isNotEmpty);
      expect(name('mystery_future_type'), isNotEmpty);
    });

    test('toJson 往返保持 wire 值串', () {
      final tx = PhotonTransaction.fromJson(_transactionJson('guest_seed'));
      expect(tx.toJson()['transaction_type'], 'guest_seed');
    });
  });
}

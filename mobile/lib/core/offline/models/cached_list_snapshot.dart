import 'package:isar/isar.dart';

part 'cached_list_snapshot.g.dart';

/// N34（A-SPEC6）：备考资产列表快照的本地 warm 缓存条目。
///
/// 机制照统计域 `CachedStatisticsModel` warm 层先例：只存**真实 API 响应**
/// 的原始 JSON（唯一后端口径的产物，本地快照只读、不构成第二事实源），
/// 离线/网络失败时回读并把时点戳传导到 UI（「截至 X」标记）。
///
/// 通用化说明：统计域按 type+period 建模，本集合面向 task / error_book /
/// community 三个读域的「列表型响应」，因此以调用方给定的 [cacheKey]
/// （域前缀 + 查询参数指纹）为唯一寻址轴，payload 保持各域原始响应形状，
/// 解析与口径归响应域所有——缓存层不做任何字段裁剪或默认值补造。
@collection
@Name('cls_2528')
class CachedListSnapshot {
  Id id = Isar.autoIncrement;

  @Index(name: 'i_cls_key_2529', unique: true)
  late String cacheKey;

  /// 原始响应 JSON（utf-8 bytes）。
  late List<int> jsonData;

  /// 数据时点戳（N36「截至 X」标记的真源）。
  late DateTime fetchedAt;

  /// 溯源版本：条目格式/口径变更时整体失效旧条目
  ///（照统计域 legacy purge 先例——版本不符的条目永不服务）。
  @Index(name: 'i_cls_ver_2530')
  String version = cacheVersion;

  /// 当前写入版本。读侧发现版本不符即视为 miss（调用方可清理）。
  static const String cacheVersion = 'v1';
}

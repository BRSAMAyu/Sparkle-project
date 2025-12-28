import 'package:lunar/lunar.dart';

class LunarService {
  factory LunarService() => _instance;
  LunarService._internal();
  static final LunarService _instance = LunarService._internal();

  /// Get Lunar date info for a given solar date
  Map<String, dynamic> getLunarInfo(DateTime date) {
    final lunar = Lunar.fromDate(date);
    
    return {
      'lunarDate': '${lunar.getMonthInChinese()}月${lunar.getDayInChinese()}',
      'year': '${lunar.getYearInGanZhi()}年 (${lunar.getYearShengXiao()})',
      'jieQi': lunar.getJieQi(),
      'festivals': lunar.getFestivals(),
      'solarTerm': lunar.getJieQi(),
    };
  }

  /// Check if a date has a festival or solar term
  String? getFestivalOrTerm(DateTime date) {
    final lunar = Lunar.fromDate(date);
    final festivals = lunar.getFestivals();
    final term = lunar.getJieQi();
    
    if (festivals.isNotEmpty) {
      return festivals.first;
    }
    if (term.isNotEmpty) {
      return term;
    }
    return null;
  }
  
  /// Get structured info for calendar cell
  LunarData getLunarData(DateTime date) {
    final lunar = Lunar.fromDate(date);
    return LunarData(
      lunarDay: lunar.getDayInChinese(),
      lunarMonth: lunar.getMonthInChinese(),
      term: lunar.getJieQi(),
      festivals: lunar.getFestivals(),
      isFestival: lunar.getFestivals().isNotEmpty,
    );
  }
}

class LunarData {

  LunarData({
    required this.lunarDay,
    required this.lunarMonth,
    required this.term,
    required this.festivals,
    required this.isFestival,
  });
  final String lunarDay;
  final String lunarMonth;
  final String term;
  final List<String> festivals;
  final bool isFestival;
  
  String get displayString {
    if (festivals.isNotEmpty) return festivals.first;
    if (term.isNotEmpty) return term;
    if (lunarDay == '初一') return '$lunarMonth月';
    return lunarDay;
  }
}

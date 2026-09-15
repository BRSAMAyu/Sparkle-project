import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

void main() {
  group('CXP-24 mobile polish', () {
    test('high-traffic task/community labels are launch copy in zh/en', () {
      final en = AppLocalizationsEn();
      final zh = AppLocalizationsZh();

      expect(en.taskListLoading, 'Loading tasks...');
      expect(en.taskListTitle, 'Tasks');
      expect(en.taskSearchHint, 'Search tasks...');

      expect(zh.taskListLoading, isNot(en.taskListLoading));
      expect(zh.taskListTitle, isNot(en.taskListTitle));
      expect(zh.taskSearchHint, isNot(en.taskSearchHint));

      expect(en.communityFavorite, 'Favorite');
      expect(zh.communityFavorite, isNot(en.communityFavorite));
      expect(en.commonShowMore, 'Show more');
      expect(zh.commonShowMore, isNot(en.commonShowMore));
    });
  });
}

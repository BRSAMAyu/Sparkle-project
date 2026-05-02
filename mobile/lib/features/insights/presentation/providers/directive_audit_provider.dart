import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/directive_audit_entry.dart';
import 'package:sparkle/features/insights/data/repositories/directive_audit_repository.dart';

final directiveAuditProvider = FutureProvider.autoDispose
    .family<List<DirectiveAuditEntry>, DirectiveAuditFilter>(
  (ref, filter) => ref.watch(directiveAuditRepositoryProvider).fetchRecent(
        limit: filter.limit,
        directiveType: filter.directiveType,
        hours: filter.hours,
      ),
);

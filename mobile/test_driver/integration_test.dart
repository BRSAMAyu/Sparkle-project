import 'package:integration_test/integration_test.dart';

// E2E test driver
// Run with: flutter drive --driver=test_driver/integration_test.dart \
//           --target=integration_test/regression_core_flow_test.dart \
//           -d <device_id>
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
}

import 'package:fixture_app/core/widgets/app_button.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

void main() {
  testWidgets('shows the label and calls onPressed on tap', (tester) async {
    var taps = 0;
    await tester.pumpApp(AppButton(label: 'Go', onPressed: () => taps++));

    expect(find.text('Go'), findsOneWidget);
    await tester.tap(find.byType(AppButton));
    expect(taps, 1);
  });
}

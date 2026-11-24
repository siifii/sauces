import 'package:fixture_app/core/widgets/app_text_field.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

void main() {
  testWidgets('shows the label and the error text', (tester) async {
    await tester.pumpApp(
      const AppTextField(label: 'Email', errorText: 'Required'),
    );

    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Required'), findsOneWidget);
  });
}

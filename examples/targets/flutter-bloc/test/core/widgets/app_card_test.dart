import 'package:fixture_app/core/widgets/app_card.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

void main() {
  testWidgets('renders its child', (tester) async {
    await tester.pumpApp(const AppCard(child: Text('Inside')));

    expect(find.text('Inside'), findsOneWidget);
  });
}

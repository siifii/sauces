import 'package:fixture_app/features/home/view/home_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/pump_app.dart';

void main() {
  testWidgets('greeting count goes up on tap and resets', (tester) async {
    await tester.pumpApp(const HomePage());
    expect(find.textContaining('nobody yet'), findsOneWidget);

    await tester.tap(find.text('Say hello'));
    await tester.pump();
    expect(find.textContaining('1 time'), findsOneWidget);

    await tester.tap(find.text('Reset'));
    await tester.pump();
    expect(find.textContaining('nobody yet'), findsOneWidget);
  });

  testWidgets('renders Arabic strings in RTL', (tester) async {
    await tester.pumpApp(const HomePage(), locale: const Locale('ar'));

    expect(find.text('الرئيسية'), findsOneWidget);
    expect(find.text('قل مرحبًا'), findsOneWidget);
  });
}

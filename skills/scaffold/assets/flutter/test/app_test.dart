import 'package:{{package}}/app.dart';
import 'package:{{package}}/features/home/view/home_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers/pump_app.dart';

void main() {
  testWidgets('App starts on the home page', (tester) async {
    await tester.pumpWidget(const App());
    await tester.pumpAndSettle();
    expect(find.byType(HomePage), findsOneWidget);
  });

  testWidgets('Home page lays out right-to-left in Arabic', (tester) async {
    await tester.pumpApp(const HomePage(), locale: const Locale('ar'));
    await tester.pumpAndSettle();
    final direction = Directionality.of(tester.element(find.byType(HomePage)));
    expect(direction, TextDirection.rtl);
  });
}

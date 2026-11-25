import 'package:flutter/material.dart';

import '../../../l10n/l10n.dart';

/// Starter page. The first screen Sauces builds replaces it as the app's home.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.appTitle)),
      body: Center(child: Text(l10n.homePlaceholder)),
    );
  }
}

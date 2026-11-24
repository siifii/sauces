import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../l10n/l10n.dart';
import '../cubit/home_cubit.dart';
import '../cubit/home_state.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => HomeCubit(),
      child: const _HomeView(),
    );
  }
}

class _HomeView extends StatelessWidget {
  const _HomeView();

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(context.l10n.homeTitle)),
      body: Padding(
        padding: const EdgeInsetsDirectional.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            BlocBuilder<HomeCubit, HomeState>(
              builder: (context, state) => AppCard(
                child: Text(
                  context.l10n.homeGreeting(state.greetings),
                  style: textTheme.bodyLarge,
                ),
              ),
            ),
            const SizedBox(height: 16),
            AppTextField(label: context.l10n.homeNameLabel),
            const SizedBox(height: 16),
            AppButton(
              label: context.l10n.homeGreetButton,
              onPressed: () => context.read<HomeCubit>().greet(),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => context.read<HomeCubit>().reset(),
              child: Text(context.l10n.homeResetButton),
            ),
          ],
        ),
      ),
    );
  }
}

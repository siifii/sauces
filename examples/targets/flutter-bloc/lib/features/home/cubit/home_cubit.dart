import 'package:flutter_bloc/flutter_bloc.dart';

import 'home_state.dart';

class HomeCubit extends Cubit<HomeState> {
  HomeCubit() : super(const HomeState());

  void greet() => emit(state.copyWith(greetings: state.greetings + 1));

  void reset() => emit(const HomeState());
}

import 'package:flutter/foundation.dart';

@immutable
class HomeState {
  const HomeState({this.greetings = 0});

  final int greetings;

  HomeState copyWith({int? greetings}) =>
      HomeState(greetings: greetings ?? this.greetings);

  @override
  bool operator ==(Object other) =>
      other is HomeState && other.greetings == greetings;

  @override
  int get hashCode => greetings.hashCode;
}

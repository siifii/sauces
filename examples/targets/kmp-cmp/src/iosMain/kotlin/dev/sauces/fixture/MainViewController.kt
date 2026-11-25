package dev.sauces.fixture

import androidx.compose.ui.window.ComposeUIViewController

fun makeFixtureViewController(state: String, rtl: Boolean) =
    ComposeUIViewController { FixtureApp(state, rtl) }

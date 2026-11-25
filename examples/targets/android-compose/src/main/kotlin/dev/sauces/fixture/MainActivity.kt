package dev.sauces.fixture

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val state = intent.getStringExtra("fixtureState") ?: "default"
        val rtl = intent.getBooleanExtra("fixtureRtl", false)
        setContent { FixtureApp(state, rtl) }
    }
}

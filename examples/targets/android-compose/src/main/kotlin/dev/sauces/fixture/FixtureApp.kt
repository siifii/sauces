package dev.sauces.fixture

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember

@Composable
fun FixtureApp(state: String = "default", rtl: Boolean = false) {
    val email = remember { mutableStateOf("") }
    val direction = if (rtl) LayoutDirection.Rtl else LayoutDirection.Ltr
    CompositionLocalProvider(LocalLayoutDirection provides direction) {
        MaterialTheme {
            Column(Modifier.padding(24.dp)) {
                AppTextField(email.value, { email.value = it }, if (rtl) "البريد الإلكتروني" else "Email")
                AppButton(if (rtl) "متابعة" else "Continue") {}
                when (state) {
                    "error" -> Text(if (rtl) "تحقق من البريد الإلكتروني" else "Check your email")
                    "loading" -> CircularProgressIndicator()
                }
            }
        }
    }
}

@Composable
fun AppButton(label: String, onClick: () -> Unit) {
    Button(onClick = onClick) { Text(text = label) }
}

@Composable
fun AppTextField(value: String, onValueChange: (String) -> Unit, label: String) {
    OutlinedTextField(value = value, onValueChange = onValueChange, label = { Text(text = label) })
}

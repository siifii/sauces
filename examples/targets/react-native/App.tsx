import {useEffect, useState} from 'react';
import {ActivityIndicator, Button, Linking, StyleSheet, Text, TextInput, View} from 'react-native';

const messages = {
  en: {email: 'Email', continue: 'Continue', error: 'Check your email'},
  ar: {email: 'البريد الإلكتروني', continue: 'متابعة', error: 'تحقق من البريد الإلكتروني'},
};

const styles = StyleSheet.create({
  form: {marginTop: 64, padding: 24, gap: 12},
});

function fixtureOptions(url: string | null | undefined) {
  const query = url?.split('?')[1]?.split('&') ?? [];
  return {error: query.includes('state=error'), loading: query.includes('state=loading'),
          rtl: query.includes('rtl=1')};
}

export function AppButton({title, onPress}: {title: string; onPress: () => void}) {
  return <Button title={title} onPress={onPress} />;
}

export function AppTextField({label, value, onChangeText}: {
  label: string; value: string; onChangeText: (text: string) => void;
}) {
  return <TextInput accessibilityLabel={label} value={value} onChangeText={onChangeText} />;
}

export default function App() {
  const [email, setEmail] = useState('');
  const [options, setOptions] = useState(() => fixtureOptions(null));
  useEffect(() => {
    let mounted = true;
    void Linking.getInitialURL().then(url => {
      if (mounted) setOptions(fixtureOptions(url));
    });
    const listener = Linking.addEventListener('url', event => setOptions(fixtureOptions(event.url)));
    return () => {
      mounted = false;
      listener.remove();
    };
  }, []);
  const copy = messages[options.rtl ? 'ar' : 'en'];
  return (
    <View style={[styles.form, {direction: options.rtl ? 'rtl' : 'ltr'}]}>
      <AppTextField label={copy.email} value={email} onChangeText={setEmail} />
      <AppButton title={copy.continue} onPress={() => {}} />
      {options.error && <Text>{copy.error}</Text>}
      {options.loading && <ActivityIndicator />}
    </View>
  );
}

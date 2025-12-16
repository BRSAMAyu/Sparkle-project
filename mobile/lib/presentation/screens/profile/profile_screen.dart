import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/screens/profile/schedule_preferences_screen.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            onPressed: () {
              ref.read(authProvider.notifier).logout();
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: user == null
          ? const Center(child: Text('Not logged in'))
          : ListView(
              children: [
                UserAccountsDrawerHeader(
                  accountName: Text(user.nickname ?? user.username),
                  accountEmail: Text(user.email),
                  currentAccountPicture: CircleAvatar(
                    child: Text(user.username[0].toUpperCase()),
                  ),
                ),
                ListTile(
                  leading: const Icon(Icons.schedule),
                  title: const Text('Schedule Preferences'),
                  subtitle: const Text('Set commute and break times for task suggestions'),
                  onTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const SchedulePreferencesScreen(),
                      ),
                    );
                  },
                ),
                const Divider(),
                // Add more profile options here
              ],
            ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'login_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Settings"),
        centerTitle: true,
      ),

      body: ListView(
        children: [

          ListTile(
            leading: const Icon(Icons.phone_android),
            title: const Text("Child Device"),
            subtitle: const Text("Connected"),
            onTap: () {
              showDialog(
                context: context,
                builder: (_) => AlertDialog(
                  title: const Text("Device Info"),
                  content: const Text("Child device is connected."),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text("OK"),
                    ),
                  ],
                ),
              );
            },
          ),

          const Divider(),

          ListTile(
            leading: const Icon(Icons.notifications),
            title: const Text("Notifications"),
            subtitle: const Text("Enabled"),
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Notifications enabled")),
              );
            },
          ),

          const Divider(),

          ListTile(
            leading: const Icon(Icons.security),
            title: const Text("Monitoring Status"),
            subtitle: const Text("Active"),
          ),

          const Divider(),

          ListTile(
            leading: const Icon(Icons.info),
            title: const Text("App Version"),
            subtitle: const Text("v1.0"),
            onTap: () {
              showAboutDialog(
                context: context,
                applicationName: "Digital Guardian",
                applicationVersion: "1.0",
              );
            },
          ),

          const Divider(),

          
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text("Logout"),
            onTap: () async {

              await FirebaseAuth.instance.signOut();

              Navigator.pushReplacement(
                context,
                MaterialPageRoute(
                  builder: (_) => const LoginScreen(),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

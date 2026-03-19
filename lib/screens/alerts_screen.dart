import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Security Alerts"),
        centerTitle: true,
      ),

      body: StreamBuilder<QuerySnapshot>(
        stream: FirebaseFirestore.instance.collection('alerts').snapshots(),
        builder: (context, snapshot) {

          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return const Center(
              child: Text(
                "No Alerts Found",
                style: TextStyle(fontSize: 18),
              ),
            );
          }

          final alerts = snapshot.data!.docs;

          return ListView.builder(
            itemCount: alerts.length,
            itemBuilder: (context, index) {

              final data = alerts[index].data() as Map<String, dynamic>;

              String alert = data['alert']?.toString() ?? "Suspicious Activity";
              String app = data['app']?.toString() ?? "Unknown App";
              String time = data['time']?.toString() ?? "Unknown Time";

              return Card(
                margin: const EdgeInsets.all(10),
                child: ListTile(
                  leading: const Icon(
                    Icons.warning,
                    color: Colors.red,
                    size: 30,
                  ),

                  title: Text(
                    alert,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                  ),

                  subtitle: Text("$app • $time"),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

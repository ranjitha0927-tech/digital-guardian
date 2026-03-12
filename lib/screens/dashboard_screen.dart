import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  // Function to add alert
     void addAlert() async {
  var now = DateTime.now();

  String time =
      "${now.hour}:${now.minute.toString().padLeft(2, '0')}";

  await FirebaseFirestore.instance.collection('alerts').add({
    'title': 'Inappropriate Content Detected',
    'description': 'Child accessed restricted website',
    'time': time,
  });
}
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Digital Guardian"),
        centerTitle: true,
      ),
      body: Column(
        children: [

          const SizedBox(height: 20),

          // Security status card
          Container(
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.green[100],
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Column(
              children: [
                Icon(Icons.security, size: 40, color: Colors.green),
                SizedBox(height: 10),
                Text(
                  "Device Secure",
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),

          const SizedBox(height: 10),

          // Scan button
          ElevatedButton(
            onPressed: () {
              addAlert();
            },
            child: const Text("Scan Device"),
          ),

          const SizedBox(height: 20),

          const Text(
            "Security Alerts",
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 10),

          Expanded(
            child: StreamBuilder<QuerySnapshot>(
              stream: FirebaseFirestore.instance
                  .collection('alerts')
                  .snapshots(),
              builder: (context, snapshot) {

                if (snapshot.connectionState ==
                    ConnectionState.waiting) {
                  return const Center(
                      child: CircularProgressIndicator());
                }

                if (!snapshot.hasData ||
                    snapshot.data!.docs.isEmpty) {
                  return const Center(
                    child: Text("No alerts found"),
                  );
                }

                final alerts = snapshot.data!.docs;

                return ListView.builder(
                  itemCount: alerts.length,
                  itemBuilder: (context, index) {

                    var data = alerts[index];

                    return Card(
                      margin: const EdgeInsets.all(10),
                      child: ListTile(
                        leading: const Icon(
                          Icons.warning,
                          color: Colors.red,
                        ),
                        title: Text(data['title']),
                        subtitle: Text(
                          "${data['description']} \n${data['time']}",
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),

          const Padding(
            padding: EdgeInsets.all(10),
            child: Text(
              "Developed by Ranjitha © 2026",
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
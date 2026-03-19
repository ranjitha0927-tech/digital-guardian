import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {

  int selectedIndex = 0;

  Future<void> scanDevice() async {
    await FirebaseFirestore.instance.collection('alerts').add({
      'alert': '18+ Content Detected',
      'app': 'Unknown App',
      'time': DateTime.now().toString(),
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Scan Completed")),
    );
  }

  Widget homePage() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [

          Icon(Icons.security, size: 100, color: Colors.blue),

          const SizedBox(height: 20),

          const Text(
            "Digital Guardian",
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 20),

          ElevatedButton(
            onPressed: scanDevice,
            child: const Text("Scan Device"),
          ),
        ],
      ),
    );
  }

  Widget alertsPage() {
    return StreamBuilder(
      stream: FirebaseFirestore.instance.collection('alerts').snapshots(),
      builder: (context, snapshot) {

        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }

        final docs = snapshot.data!.docs;

        if (docs.isEmpty) {
          return const Center(child: Text("No Alerts Found"));
        }

        return ListView(
          children: docs.map((doc) {

            final data = doc.data() as Map;

            return ListTile(
              leading: const Icon(Icons.warning, color: Colors.red),
              title: Text(data['alert']),
              subtitle: Text("${data['app']} - ${data['time']}"),
            );

          }).toList(),
        );
      },
    );
  }

  Widget reportsPage() {
    return const Center(
      child: Text(
        "Reports Page",
        style: TextStyle(fontSize: 18),
      ),
    );
  }

  Widget settingsPage() {
    return const Center(
      child: Text(
        "Settings Page",
        style: TextStyle(fontSize: 18),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {

    final pages = [
      homePage(),
      alertsPage(),
      reportsPage(),
      settingsPage(),
    ];

    return Scaffold(

      appBar: AppBar(
        title: const Text("Digital Guardian"),
        centerTitle: true,
      ),

      body: pages[selectedIndex],

      bottomNavigationBar: BottomNavigationBar(
  currentIndex: selectedIndex,
  selectedItemColor: Colors.blue,
  unselectedItemColor: Colors.grey,

  onTap: (index) {
    setState(() {
      selectedIndex = index;
    });
  },

  items: const [
    BottomNavigationBarItem(
      icon: Icon(Icons.home),
      label: "Home",
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.warning),
      label: "Alerts",
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.bar_chart),
      label: "Reports",
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.settings),
      label: "Settings",
    ),
  ],
),

          

      bottomSheet: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(10),
        color: Colors.grey[200],
        child: const Text(
          "Developed by Ranjitha ©2026",
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

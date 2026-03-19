import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'alerts_screen.dart';
import 'reports_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {

  int selectedIndex = 0;

  
  Future<void> generateAutoAlert() async {
    await FirebaseFirestore.instance.collection('alerts').add({
      'alert': '18+ Website Detected',
      'app': 'Chrome Browser',
      'time': DateTime.now().toString(),
    });
  }


  void showAlertPopup() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("⚠️ Alert"),
        content: const Text("Suspicious activity detected!"),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("OK"),
          ),
        ],
      ),
    );
  }

  final List<Widget> pages = [
    const HomePage(),
    const AlertsScreen(),
    const ReportsScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),

      appBar: AppBar(
        title: const Text("Digital Guardian"),
        centerTitle: true,
        backgroundColor: Colors.blueAccent,
      ),

      body: pages[selectedIndex],

      bottomNavigationBar: BottomNavigationBar(
        currentIndex: selectedIndex,
        selectedItemColor: Colors.blueAccent,
        unselectedItemColor: Colors.grey,

        onTap: (index) {
          setState(() {
            selectedIndex = index;
          });
        },

        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: "Home"),
          BottomNavigationBarItem(icon: Icon(Icons.warning), label: "Alerts"),
          BottomNavigationBarItem(icon: Icon(Icons.bar_chart), label: "Reports"),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: "Settings"),
        ],
      ),
    );
  }
}



class HomePage extends StatelessWidget {
  const HomePage({super.key});

  
  Widget build(BuildContext context) {

    final parent = context.findAncestorStateOfType<_HomeScreenState>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),

      child: Column(
        children: [

          // LOGO
          Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: Colors.blueAccent,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.security, size: 80, color: Colors.white),
          ),

          const SizedBox(height: 15),

          const Text(
            "Digital Guardian",
            style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 10),

          const Text(
            "Protecting children from harmful apps and websites.",
            textAlign: TextAlign.center,
          ),

          const SizedBox(height: 25),

        
          Card(
            elevation: 5,
            child: ListTile(
              leading: const Icon(Icons.phone_android, color: Colors.blue),
              title: const Text("Child Device"),
              subtitle: const Text("Connected"),
              onTap: () {
                showDialog(
                  context: context,
                  builder: (_) => AlertDialog(
                    title: const Text("Device Info"),
                    content: const Text("Child device is connected successfully."),
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
          ),

          const SizedBox(height: 10),

          
          Card(
            elevation: 5,
            child: ListTile(
              leading: const Icon(Icons.security, color: Colors.green),
              title: const Text("Monitoring Status"),
              subtitle: const Text("Active"),
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Monitoring is running")),
                );
              },
            ),
          ),

          const SizedBox(height: 10),

          
          Card(
            elevation: 5,
            child: ListTile(
              leading: const Icon(Icons.notifications, color: Colors.orange),
              title: const Text("Recent Activity"),
              subtitle: const Text("Tap to view alerts"),
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const AlertsScreen()),
                );
              },
            ),
          ),

          const SizedBox(height: 25),

          
          ElevatedButton.icon(
            icon: const Icon(Icons.search),
            label: const Text("Scan Device"),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blueAccent,
              padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
            ),
            onPressed: () async {

              await parent?.generateAutoAlert();

              parent?.showAlertPopup();

              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text("Scan completed")),
              );
            },
          ),

          const SizedBox(height: 30),

          const Text(
            "Stay aware. Stay protected.",
            style: TextStyle(fontStyle: FontStyle.italic),
          ),

          const SizedBox(height: 15),

          const Text(
            "Developed by Ranjitha ©2026",
            style: TextStyle(color: Colors.grey),
          ),
        ],
      ),
    );
  }
}
    

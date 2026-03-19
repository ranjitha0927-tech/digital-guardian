import 'package:flutter/material.dart';

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Activity Reports"),
        centerTitle: true,
      ),

      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [

            Icon(
              Icons.bar_chart,
              size: 90,
              color: Colors.blue,
            ),

            SizedBox(height: 20),

            Text(
              "Weekly Monitoring Report",
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),

            SizedBox(height: 15),

            Text("• Suspicious apps detected: 2"),
            Text("• Blocked websites: 3"),
            Text("• Screen usage today: 4 hours"),
            Text("• Unsafe content attempts: 1"),
          ],
        ),
      ),
    );
  }
}

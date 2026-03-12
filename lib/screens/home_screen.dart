import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(height: 20),
            Text(
              "Welcome Parent 👋",
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 20),
            Card(
              child: ListTile(
                leading: Icon(Icons.phone_android, color: Colors.green),
                title: Text("Child Device Status"),
                subtitle: Text("Connected"),
              ),
            ),
            SizedBox(height: 10),
            Card(
              child: ListTile(
                leading: Icon(Icons.access_time, color: Colors.green),
                title: Text("Today's Screen Time"),
                subtitle: Text("3 Hours 20 Minutes"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
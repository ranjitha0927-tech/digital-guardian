import 'package:flutter/material.dart';

class AlertsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Alerts"),
        backgroundColor: Colors.green,
      ),
      body: ListView(
        padding: EdgeInsets.all(16),
        children: [

          alertCard(
            Icons.warning,
            "Blocked Website Attempt",
            "Child tried accessing restricted site",
            "2 mins ago",
            Colors.red,
          ),

          alertCard(
            Icons.access_time,
            "Screen Time Limit Exceeded",
            "Device used beyond allowed time",
            "1 hour ago",
            Colors.orange,
          ),

          alertCard(
            Icons.location_on,
            "Location Update",
            "Child reached school area",
            "Today 8:45 AM",
            Colors.blue,
          ),
        ],
      ),
    );
  }

  Widget alertCard(IconData icon, String title, String subtitle,
      String time, Color color) {
    return Card(
      margin: EdgeInsets.only(bottom: 15),
      elevation: 3,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(15),
      ),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: color.withOpacity(0.2),
          child: Icon(icon, color: color),
        ),
        title: Text(title, style: TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle),
        trailing: Text(
          time,
          style: TextStyle(fontSize: 12, color: Colors.grey),
        ),
      ),
    );
  }
}
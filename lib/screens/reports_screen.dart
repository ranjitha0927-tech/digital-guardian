import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

class ReportsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Weekly Screen Time"),
        backgroundColor: Colors.green,
      ),
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          children: [
            SizedBox(height: 20),
            Expanded(
              child: BarChart(
                BarChartData(
                  borderData: FlBorderData(show: false),
                  titlesData: FlTitlesData(
                    show: true,
                  ),
                  barGroups: [
                    makeGroupData(0, 2),
                    makeGroupData(1, 3),
                    makeGroupData(2, 4),
                    makeGroupData(3, 1.5),
                    makeGroupData(4, 3.5),
                    makeGroupData(5, 2.5),
                    makeGroupData(6, 4.5),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  BarChartGroupData makeGroupData(int x, double y) {
    return BarChartGroupData(
      x: x,
      barRods: [
        BarChartRodData(
          toY: y,
          width: 18,
          color: Colors.green,
          borderRadius: BorderRadius.circular(6),
        ),
      ],
    );
  }
}
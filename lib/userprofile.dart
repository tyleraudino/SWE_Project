import 'package:flutter/material.dart';
import 'opening.dart';
import 'package:provider/provider.dart';
import 'user_provider.dart';
import 'change_email.dart';
import 'change_password.dart';
import 'change_username.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<UserProvider>(
      builder: (context, userProvider, child) {
        return Scaffold(
          appBar: AppBar(
            title: const Text('Pawsitive Minds'),
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center, // center
              children: [
                Center(
                  child: Image.asset(
                    'assets/catGif.gif',
                    width: 250,
                    height: 250,
                    fit: BoxFit.contain,
                  ),
                ),
                const SizedBox(height: 32),
                
                Row(
                  mainAxisAlignment: MainAxisAlignment.center, // center content
                  children: [
                    _ProfileInfoTile(
                      title: 'Email',
                      value: userProvider.user.email,
                    ),
                    const SizedBox(width: 16),
                    _ProfileInfoTile(
                      title: 'Username',
                      value: userProvider.user.username,
                    ),
                  ],
                ),
                const SizedBox(height: 32),
                
                // buttons
                ElevatedButton(
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(builder: (context) => ChangeEmail()),
                    );
                  },
                  child: const Text('Change Email'),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(builder: (context) => ChangeUsername()),
                    );
                  },
                  child: const Text('Change Username'),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(builder: (context) => ChangePassword()),
                    );
                  },
                  child: const Text('Change Password'),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(builder: (context) => OpeningPage()),
                    );
                  },
                  child: const Text('Log Out'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ProfileInfoTile extends StatelessWidget {
  final String title;
  final String value;

  const _ProfileInfoTile({
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          title,
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text(value),
      ],
    );
  }
}

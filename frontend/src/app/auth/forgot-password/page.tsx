'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';
import Link from 'next/link';

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      // Simulate API call - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      toast({
        title: "Reset link sent!",
        description: "Check your email for password reset instructions.",
        variant: "success",
      });
      
      setIsSubmitted(true);
    } catch (error) {
      toast({
        title: "Failed to send reset link",
        description: "Please try again or contact support if the problem persists.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-blue-500/10 flex items-center justify-center p-4">
        {/* Background Elements */}
        <div className="absolute inset-0 overflow-hidden">
          <motion.div
            className="absolute top-1/3 left-1/4 w-64 h-64 bg-green-500/10 rounded-full blur-3xl"
            animate={{
              x: [0, 80, 0],
              y: [0, -40, 0],
              scale: [1, 1.1, 1],
            }}
            transition={{
              duration: 15,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        </div>

        <div className="w-full max-w-md relative z-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
          >
            <Card className="border-0 shadow-2xl shadow-green-500/10 bg-card/80 backdrop-blur-lg">
              <CardHeader className="text-center pb-6">
                <motion.div
                  className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl mb-4 mx-auto"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ duration: 0.6, delay: 0.2 }}
                >
                  <motion.span
                    className="text-2xl text-white"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.6, delay: 0.4 }}
                  >
                    ✓
                  </motion.span>
                </motion.div>
                <CardTitle className="text-2xl font-bold text-green-600">Check Your Email</CardTitle>
                <CardDescription className="text-base">
                  We've sent a password reset link to
                  <br />
                  <span className="font-medium text-foreground">{email}</span>
                </CardDescription>
              </CardHeader>
              
              <CardContent className="space-y-4">
                <div className="bg-muted/50 p-4 rounded-lg">
                  <h4 className="font-medium mb-2">What's next?</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Check your email inbox (and spam folder)</li>
                    <li>• Click the reset link in the email</li>
                    <li>• Create a new secure password</li>
                    <li>• Sign in with your new password</li>
                  </ul>
                </div>
                
                <div className="text-center text-sm text-muted-foreground">
                  Didn't receive an email?{' '}
                  <button
                    onClick={() => {
                      setIsSubmitted(false);
                      setEmail('');
                    }}
                    className="text-primary hover:text-primary/80 font-medium"
                  >
                    Try again
                  </button>
                </div>
                
                <Link href="/auth/signin">
                  <Button variant="outline" className="w-full">
                    Back to Sign In
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary/5 via-background to-blue-500/10 flex items-center justify-center p-4">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          className="absolute top-1/4 right-1/3 w-72 h-72 bg-primary/10 rounded-full blur-3xl"
          animate={{
            x: [0, -60, 0],
            y: [0, 40, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute bottom-1/3 left-1/4 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl"
          animate={{
            x: [0, 80, 0],
            y: [0, -60, 0],
            scale: [1, 0.8, 1],
          }}
          transition={{
            duration: 18,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      </div>

      <div className="w-full max-w-md relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20, rotateX: -15 }}
          animate={{ opacity: 1, y: 0, rotateX: 0 }}
          transition={{ duration: 0.6 }}
          style={{ perspective: '1000px' }}
        >
          {/* Logo and Header */}
          <motion.div 
            className="text-center mb-8"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary to-blue-600 rounded-2xl mb-4 transform rotate-6">
              <span className="text-2xl font-bold text-white">S</span>
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">
              Reset Password
            </h1>
            <p className="text-muted-foreground mt-2">
              Enter your email to receive a reset link
            </p>
          </motion.div>

          {/* Reset Password Card */}
          <motion.div
            whileHover={{ 
              rotateY: 1,
              scale: 1.01,
            }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-0 shadow-2xl shadow-primary/10 bg-card/80 backdrop-blur-lg">
              <CardHeader className="space-y-1 pb-6">
                <CardTitle className="text-2xl font-bold">Forgot Password?</CardTitle>
                <CardDescription>
                  No worries! Enter your email address and we'll send you a link to reset your password.
                </CardDescription>
              </CardHeader>
              
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Email Field */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none">
                      Email Address
                    </label>
                    <motion.div
                      whileFocus={{ scale: 1.02 }}
                      transition={{ duration: 0.2 }}
                    >
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="flex h-11 w-full rounded-lg border border-input bg-background/50 px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 transition-all duration-200"
                        placeholder="Enter your email address"
                      />
                    </motion.div>
                    {email && !validateEmail(email) && (
                      <p className="text-sm text-red-500">Please enter a valid email address</p>
                    )}
                  </div>

                  {/* Submit Button */}
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Button
                      type="submit"
                      disabled={isLoading || !email || !validateEmail(email)}
                      className="w-full h-11 bg-gradient-to-r from-primary to-blue-600 hover:from-primary/90 hover:to-blue-600/90 text-white font-medium transition-all duration-300"
                    >
                      {isLoading ? (
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Sending reset link...
                        </div>
                      ) : (
                        'Send Reset Link'
                      )}
                    </Button>
                  </motion.div>

                  {/* Additional Info */}
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <div className="flex items-start gap-3">
                      <div className="text-primary text-lg">💡</div>
                      <div>
                        <h4 className="font-medium text-sm mb-1">Security Tip</h4>
                        <p className="text-xs text-muted-foreground">
                          The reset link will expire in 1 hour for security reasons. 
                          If you don't receive an email, check your spam folder.
                        </p>
                      </div>
                    </div>
                  </div>
                </form>

                {/* Navigation Links */}
                <div className="mt-6 flex flex-col gap-4">
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t border-border" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-card px-2 text-muted-foreground">Or</span>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-2">
                    <Link href="/auth/signin" className="flex-1">
                      <Button variant="outline" className="w-full">
                        Back to Sign In
                      </Button>
                    </Link>
                    <Link href="/auth/signup" className="flex-1">
                      <Button variant="ghost" className="w-full">
                        Create Account
                      </Button>
                    </Link>
                  </div>
                </div>

                {/* Contact Support */}
                <div className="mt-6 text-center">
                  <p className="text-sm text-muted-foreground">
                    Still having trouble?{' '}
                    <Link 
                      href="/contact" 
                      className="font-medium text-primary hover:text-primary/80 transition-colors"
                    >
                      Contact support
                    </Link>
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage; 
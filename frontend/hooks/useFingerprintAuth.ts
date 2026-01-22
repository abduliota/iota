import { useState, useEffect } from 'react';

const AUTH_STORAGE_KEY = 'ksa_regtech_auth';
const CREDENTIAL_STORAGE_KEY = 'ksa_regtech_credential';

interface AuthUser {
  email: string;
  credentialId: string;
  authenticatedAt: number;
}

export function useFingerprintAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = () => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    const authData = localStorage.getItem(AUTH_STORAGE_KEY);
    if (authData) {
      try {
        const user = JSON.parse(authData);
        setUser(user);
        setIsAuthenticated(true);
      } catch {
        setIsAuthenticated(false);
      }
    }
    setIsLoading(false);
  };

  const register = async (email: string): Promise<{ success: boolean; error?: string }> => {
    if (!window.PublicKeyCredential) {
      return { success: false, error: 'WebAuthn not supported in this browser' };
    }

    try {
      // Handle rpId for localhost/development
      const rpId = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'localhost'
        : window.location.hostname;

      const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
        challenge: crypto.getRandomValues(new Uint8Array(32)),
        rp: {
          name: 'KSA RegTech',
          id: rpId,
        },
        user: {
          id: new TextEncoder().encode(email),
          name: email,
          displayName: email,
        },
        pubKeyCredParams: [
          { alg: -7, type: 'public-key' },   // ES256
          { alg: -257, type: 'public-key' }, // RS256
        ],
        authenticatorSelection: {
          userVerification: 'preferred',
        },
        timeout: 60000,
        attestation: 'none',
      };

      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions,
      }) as PublicKeyCredential;

      if (credential) {
        const authUser: AuthUser = {
          email,
          credentialId: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
          authenticatedAt: Date.now(),
        };

        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
        localStorage.setItem(CREDENTIAL_STORAGE_KEY, JSON.stringify({
          id: credential.id,
          rawId: Array.from(new Uint8Array(credential.rawId)),
        }));

        setUser(authUser);
        setIsAuthenticated(true);
        return { success: true };
      }

      return { success: false, error: 'Registration failed' };
    } catch (error: any) {
      let errorMessage = 'Registration failed';
      if (error.name === 'NotAllowedError') {
        errorMessage = 'Fingerprint authentication was cancelled or not available';
      } else if (error.name === 'TimeoutError') {
        errorMessage = 'Fingerprint authentication timed out. Please try again.';
      } else if (error.message) {
        errorMessage = error.message;
      }
      return { success: false, error: errorMessage };
    }
  };

  const login = async (email: string): Promise<{ success: boolean; error?: string }> => {
    if (!window.PublicKeyCredential) {
      return { success: false, error: 'WebAuthn not supported in this browser' };
    }

    try {
      const storedCredential = localStorage.getItem(CREDENTIAL_STORAGE_KEY);
      if (!storedCredential) {
        return { success: false, error: 'No credential found. Please sign up first.' };
      }

      const credentialData = JSON.parse(storedCredential);
      const credentialId = Uint8Array.from(credentialData.rawId);

      // Handle rpId for localhost/development
      const rpId = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'localhost'
        : window.location.hostname;

      const publicKeyCredentialRequestOptions: PublicKeyCredentialRequestOptions = {
        challenge: crypto.getRandomValues(new Uint8Array(32)),
        rpId: rpId,
        allowCredentials: [{
          id: credentialId,
          type: 'public-key',
        }],
        timeout: 60000,
        userVerification: 'preferred',
      };

      const assertion = await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions,
      }) as PublicKeyCredential;

      if (assertion) {
        const authUser: AuthUser = {
          email,
          credentialId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
          authenticatedAt: Date.now(),
        };

        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
        setUser(authUser);
        setIsAuthenticated(true);
        return { success: true };
      }

      return { success: false, error: 'Authentication failed' };
    } catch (error: any) {
      let errorMessage = 'Authentication failed';
      if (error.name === 'NotAllowedError') {
        errorMessage = 'Fingerprint authentication was cancelled or not available';
      } else if (error.name === 'TimeoutError') {
        errorMessage = 'Fingerprint authentication timed out. Please try again.';
      } else if (error.message) {
        errorMessage = error.message;
      }
      return { success: false, error: errorMessage };
    }
  };

  const logout = () => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(CREDENTIAL_STORAGE_KEY);
    setUser(null);
    setIsAuthenticated(false);
  };

  return { isAuthenticated, user, isLoading, register, login, logout };
}

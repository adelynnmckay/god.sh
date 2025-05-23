class GodSh < Formula
  desc "In the beginning God created the heaven and the earth..."
  homepage "https://github.com/adelynnmckay/god.sh"
  url "https://github.com/adelynnmckay/god.sh/archive/refs/tags/v1.0.4.tar.gz"
  sha256 "3f9b044b7525a12688f134d763099825aa54c9ed3cd29f2dd9107af94b8270ce"
  version "1.0.4"
  license "MIT"

  def install
    bin.install "god.sh"
  end

  def caveats
    <<~EOS
      To complete installation, run:
        god.sh let-there-be-light
    EOS
  end

  test do
    system "#{bin}/god.sh", "--help"
  end
end

